"""
Test script for AlphaTrend indicator
"""
import sys
import os

# Add user_data/strategies to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'user_data', 'strategies'))

def test_alphatrend_import():
    """Test that AlphaTrend can be imported"""
    try:
        from kivanc_indicators import alphatrend
        print("✓ AlphaTrend function imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_alphatrend_signature():
    """Test that AlphaTrend has correct signature"""
    from kivanc_indicators import alphatrend
    import inspect

    sig = inspect.signature(alphatrend)
    params = list(sig.parameters.keys())

    expected_params = ['dataframe', 'atr_period', 'atr_multiplier', 'mfi_period']

    if params == expected_params:
        print(f"✓ Function signature correct: {params}")
        return True
    else:
        print(f"✗ Function signature mismatch. Expected {expected_params}, got {params}")
        return False

def test_alphatrend_defaults():
    """Test that default parameters are correct"""
    from kivanc_indicators import alphatrend
    import inspect

    sig = inspect.signature(alphatrend)

    defaults = {
        'atr_period': 14,
        'atr_multiplier': 1.0,
        'mfi_period': 14
    }

    all_correct = True
    for param_name, expected_value in defaults.items():
        actual_value = sig.parameters[param_name].default
        if actual_value == expected_value:
            print(f"✓ {param_name} default = {actual_value}")
        else:
            print(f"✗ {param_name} default mismatch. Expected {expected_value}, got {actual_value}")
            all_correct = False

    return all_correct

def test_alphatrend_docstring():
    """Test that docstring exists and mentions key concepts"""
    from kivanc_indicators import alphatrend

    doc = alphatrend.__doc__

    if not doc:
        print("✗ No docstring found")
        return False

    key_terms = ['AlphaTrend', 'Kıvanç', 'ATR', 'MFI', 'upT', 'downT']
    missing = [term for term in key_terms if term not in doc]

    if missing:
        print(f"✗ Docstring missing key terms: {missing}")
        return False
    else:
        print(f"✓ Docstring complete with all key terms")
        return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("AlphaTrend Indicator Test Suite")
    print("=" * 60)
    print()

    tests = [
        ("Import Test", test_alphatrend_import),
        ("Signature Test", test_alphatrend_signature),
        ("Defaults Test", test_alphatrend_defaults),
        ("Docstring Test", test_alphatrend_docstring),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! AlphaTrend implementation complete.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
