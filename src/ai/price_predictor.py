"""
LSTM Price Predictor
====================
Deep learning model for price direction prediction.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass
import logging
import os
import joblib

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Price prediction result."""
    direction: str  # 'up', 'down', 'neutral'
    probability: float  # 0.0 to 1.0
    predicted_change: float  # Predicted percentage change
    confidence: str  # 'high', 'medium', 'low'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction,
            "probability": round(self.probability, 4),
            "predicted_change": round(self.predicted_change, 4),
            "confidence": self.confidence,
        }


if TORCH_AVAILABLE:
    class LSTMModel(nn.Module):
        """LSTM Neural Network for price prediction."""
        
        def __init__(
            self,
            input_size: int = 5,
            hidden_size: int = 64,
            num_layers: int = 2,
            dropout: float = 0.2,
            output_size: int = 1
        ):
            super(LSTMModel, self).__init__()
            
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            
            self.lstm = nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0
            )
            
            self.fc = nn.Sequential(
                nn.Linear(hidden_size, 32),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(32, output_size),
                nn.Tanh()  # Output between -1 and 1
            )
        
        def forward(self, x):
            # LSTM forward
            lstm_out, _ = self.lstm(x)
            
            # Take only the last output
            last_output = lstm_out[:, -1, :]
            
            # Fully connected layers
            output = self.fc(last_output)
            
            return output


class LSTMPricePredictor:
    """
    LSTM-based price direction predictor.
    
    Uses historical OHLCV data to predict future price direction.
    
    Features used:
    - Open, High, Low, Close (normalized)
    - Volume (normalized)
    - Returns
    - Technical indicators (optional)
    """
    
    DEFAULT_SEQUENCE_LENGTH = 20  # Days of history to use
    DEFAULT_PREDICTION_HORIZON = 1  # Days ahead to predict
    
    def __init__(
        self,
        sequence_length: int = DEFAULT_SEQUENCE_LENGTH,
        prediction_horizon: int = DEFAULT_PREDICTION_HORIZON,
        hidden_size: int = 64,
        num_layers: int = 2,
        device: Optional[str] = None,
        model_dir: Optional[str] = None
    ):
        """
        Initialize the predictor.
        
        Args:
            sequence_length: Number of historical bars to use
            prediction_horizon: Number of bars ahead to predict
            hidden_size: LSTM hidden layer size
            num_layers: Number of LSTM layers
            device: Device to use ('cuda', 'cpu', or None for auto)
            model_dir: Directory to save/load models
        """
        self.sequence_length = sequence_length
        self.prediction_horizon = prediction_horizon
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.model_dir = model_dir or "./models"
        
        # Determine device
        if not TORCH_AVAILABLE:
            self.device = "cpu"
            self._model = None
            logger.warning("PyTorch not available. Using fallback predictor.")
        elif device:
            self.device = device
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"
        
        self._model = None
        self._scaler = MinMaxScaler()
        self._trained = False
        
        # Feature columns
        self.feature_cols = ['open', 'high', 'low', 'close', 'volume']
    
    def _prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare features from dataframe."""
        # Ensure we have required columns
        df = df.copy()
        
        for col in self.feature_cols:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")
        
        # Calculate additional features
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=5).std()
        df['momentum'] = df['close'].pct_change(5)
        
        # Fill NaN
        df = df.fillna(0)
        
        # Select features
        feature_cols = self.feature_cols + ['returns', 'volatility', 'momentum']
        features = df[feature_cols].values
        
        return features
    
    def _create_sequences(
        self, 
        data: np.ndarray, 
        target: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training."""
        X, y = [], []
        
        for i in range(len(data) - self.sequence_length - self.prediction_horizon + 1):
            X.append(data[i:i + self.sequence_length])
            y.append(target[i + self.sequence_length + self.prediction_horizon - 1])
        
        return np.array(X), np.array(y)
    
    def train(
        self,
        df: pd.DataFrame,
        epochs: int = 50,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train the LSTM model.
        
        Args:
            df: DataFrame with OHLCV data
            epochs: Number of training epochs
            batch_size: Batch size
            learning_rate: Learning rate
            validation_split: Validation data fraction
            
        Returns:
            Training history
        """
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not available. Cannot train model.")
            return {"error": "PyTorch not available"}
        
        logger.info("Preparing data for training...")
        
        # Prepare features
        features = self._prepare_features(df)
        
        # Calculate target (future returns)
        future_returns = df['close'].pct_change(self.prediction_horizon).shift(-self.prediction_horizon).values
        
        # Scale features
        scaled_features = self._scaler.fit_transform(features)
        
        # Create sequences
        X, y = self._create_sequences(scaled_features, future_returns[:-self.prediction_horizon])
        
        # Remove NaN targets
        valid_mask = ~np.isnan(y)
        X = X[valid_mask]
        y = y[valid_mask]
        
        # Clip target to reasonable range
        y = np.clip(y, -0.1, 0.1)  # Cap at 10% move
        
        # Train/val split
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, shuffle=False
        )
        
        # Convert to tensors
        X_train = torch.FloatTensor(X_train).to(self.device)
        y_train = torch.FloatTensor(y_train).unsqueeze(1).to(self.device)
        X_val = torch.FloatTensor(X_val).to(self.device)
        y_val = torch.FloatTensor(y_val).unsqueeze(1).to(self.device)
        
        # Create DataLoader
        train_dataset = TensorDataset(X_train, y_train)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        # Initialize model
        input_size = X.shape[2]  # Number of features
        self._model = LSTMModel(
            input_size=input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers
        ).to(self.device)
        
        # Loss and optimizer
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self._model.parameters(), lr=learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5
        )
        
        # Training loop
        history = {"train_loss": [], "val_loss": []}
        best_val_loss = float('inf')
        
        logger.info(f"Training LSTM model for {epochs} epochs...")
        
        for epoch in range(epochs):
            # Training
            self._model.train()
            train_losses = []
            
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = self._model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                train_losses.append(loss.item())
            
            avg_train_loss = np.mean(train_losses)
            
            # Validation
            self._model.eval()
            with torch.no_grad():
                val_outputs = self._model(X_val)
                val_loss = criterion(val_outputs, y_val).item()
            
            history["train_loss"].append(avg_train_loss)
            history["val_loss"].append(val_loss)
            
            # Learning rate scheduling
            scheduler.step(val_loss)
            
            # Save best model
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                self._save_model("best_model.pt")
            
            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch + 1}/{epochs} - Train Loss: {avg_train_loss:.6f}, Val Loss: {val_loss:.6f}")
        
        self._trained = True
        logger.info(f"Training complete. Best validation loss: {best_val_loss:.6f}")
        
        return history
    
    def predict(self, df: pd.DataFrame) -> PredictionResult:
        """
        Predict future price direction.
        
        Args:
            df: DataFrame with recent OHLCV data (at least sequence_length rows)
            
        Returns:
            PredictionResult with direction and probability
        """
        if not TORCH_AVAILABLE or self._model is None:
            # Fallback: simple momentum-based prediction
            return self._fallback_predict(df)
        
        if len(df) < self.sequence_length:
            raise ValueError(f"Need at least {self.sequence_length} rows of data")
        
        # Prepare features
        features = self._prepare_features(df.tail(self.sequence_length + 10))
        
        # Scale
        scaled_features = self._scaler.transform(features)
        
        # Take last sequence
        sequence = scaled_features[-self.sequence_length:]
        
        # Convert to tensor
        X = torch.FloatTensor(sequence).unsqueeze(0).to(self.device)
        
        # Predict
        self._model.eval()
        with torch.no_grad():
            prediction = self._model(X).cpu().numpy()[0, 0]
        
        # Convert to direction
        predicted_change = float(prediction) * 100  # Convert to percentage
        
        if predicted_change > 1.0:
            direction = "up"
            probability = min(0.5 + abs(predicted_change) / 20, 0.95)
        elif predicted_change < -1.0:
            direction = "down"
            probability = min(0.5 + abs(predicted_change) / 20, 0.95)
        else:
            direction = "neutral"
            probability = 1 - abs(predicted_change) / 2
        
        # Determine confidence
        if probability > 0.75:
            confidence = "high"
        elif probability > 0.6:
            confidence = "medium"
        else:
            confidence = "low"
        
        return PredictionResult(
            direction=direction,
            probability=probability,
            predicted_change=predicted_change,
            confidence=confidence
        )
    
    def _fallback_predict(self, df: pd.DataFrame) -> PredictionResult:
        """Simple fallback prediction using momentum."""
        if len(df) < 10:
            return PredictionResult(
                direction="neutral",
                probability=0.5,
                predicted_change=0.0,
                confidence="low"
            )
        
        # Calculate momentum indicators
        close = df['close']
        
        # Short-term momentum
        short_momentum = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] * 100
        
        # Medium-term momentum
        medium_momentum = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10] * 100
        
        # Combined momentum
        momentum = (short_momentum * 0.6 + medium_momentum * 0.4)
        
        if momentum > 2:
            direction = "up"
            probability = min(0.5 + momentum / 20, 0.8)
        elif momentum < -2:
            direction = "down"
            probability = min(0.5 + abs(momentum) / 20, 0.8)
        else:
            direction = "neutral"
            probability = 0.5
        
        return PredictionResult(
            direction=direction,
            probability=probability,
            predicted_change=momentum,
            confidence="low"  # Fallback is always low confidence
        )
    
    def _save_model(self, filename: str):
        """Save model to file."""
        if not TORCH_AVAILABLE or self._model is None:
            return
        
        os.makedirs(self.model_dir, exist_ok=True)
        
        filepath = os.path.join(self.model_dir, filename)
        torch.save({
            'model_state_dict': self._model.state_dict(),
            'scaler': self._scaler,
            'sequence_length': self.sequence_length,
            'hidden_size': self.hidden_size,
            'num_layers': self.num_layers,
        }, filepath)
        
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filename: str = "best_model.pt"):
        """Load model from file."""
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not available. Cannot load model.")
            return False
        
        filepath = os.path.join(self.model_dir, filename)
        
        if not os.path.exists(filepath):
            logger.warning(f"Model file not found: {filepath}")
            return False
        
        try:
            checkpoint = torch.load(filepath, map_location=self.device)
            
            self._scaler = checkpoint['scaler']
            self.sequence_length = checkpoint['sequence_length']
            self.hidden_size = checkpoint['hidden_size']
            self.num_layers = checkpoint['num_layers']
            
            # Recreate model
            self._model = LSTMModel(
                input_size=8,  # 5 OHLCV + 3 derived features
                hidden_size=self.hidden_size,
                num_layers=self.num_layers
            ).to(self.device)
            
            self._model.load_state_dict(checkpoint['model_state_dict'])
            self._trained = True
            
            logger.info(f"Model loaded from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def get_trading_signal(self, prediction: PredictionResult) -> Dict[str, Any]:
        """Convert prediction to trading signal."""
        if prediction.confidence == "high":
            if prediction.direction == "up":
                signal = "BUY"
            elif prediction.direction == "down":
                signal = "SELL"
            else:
                signal = "HOLD"
        elif prediction.confidence == "medium":
            if prediction.direction == "up":
                signal = "WEAK_BUY"
            elif prediction.direction == "down":
                signal = "WEAK_SELL"
            else:
                signal = "HOLD"
        else:
            signal = "HOLD"
        
        return {
            "signal": signal,
            "direction": prediction.direction,
            "probability": prediction.probability,
            "confidence": prediction.confidence,
            "predicted_change": prediction.predicted_change,
        }


if __name__ == "__main__":
    # Test LSTM predictor
    import yfinance as yf
    
    logging.basicConfig(level=logging.INFO)
    
    print("Testing LSTM Price Predictor...")
    print(f"PyTorch available: {TORCH_AVAILABLE}")
    
    # Fetch test data
    ticker = yf.Ticker("AAPL")
    df = ticker.history(period="2y", interval="1d")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    
    print(f"\nData shape: {df.shape}")
    
    # Initialize predictor
    predictor = LSTMPricePredictor(
        sequence_length=20,
        prediction_horizon=1,
        hidden_size=32,
        num_layers=2
    )
    
    if TORCH_AVAILABLE:
        print("\n=== Training LSTM Model ===")
        
        # Train on subset for quick test
        train_df = df.iloc[:-50]
        history = predictor.train(train_df, epochs=20, batch_size=16)
        
        print(f"\nFinal train loss: {history['train_loss'][-1]:.6f}")
        print(f"Final val loss: {history['val_loss'][-1]:.6f}")
    
    print("\n=== Making Prediction ===")
    
    # Predict on recent data
    test_df = df.iloc[-30:]
    prediction = predictor.predict(test_df)
    
    print(f"Direction: {prediction.direction}")
    print(f"Probability: {prediction.probability:.2%}")
    print(f"Predicted Change: {prediction.predicted_change:.2f}%")
    print(f"Confidence: {prediction.confidence}")
    
    print("\n=== Trading Signal ===")
    signal = predictor.get_trading_signal(prediction)
    print(f"Signal: {signal['signal']}")
