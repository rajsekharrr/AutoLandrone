"""
AutoLandrone System Verification Script

Validates all components are properly installed and functioning.
"""

import sys
import os

def check_dependencies():
    """Check all required dependencies are installed."""
    print("=" * 70)
    print("CHECKING DEPENDENCIES")
    print("=" * 70)

    required = [
        'streamlit', 'numpy', 'pandas', 'cv2', 'sklearn',
        'plotly', 'pytest', 'joblib'
    ]

    missing = []
    for module in required:
        try:
            if module == 'cv2':
                __import__('cv2')
                print(f"✓ opencv-python-headless")
            elif module == 'sklearn':
                __import__('sklearn')
                print(f"✓ scikit-learn")
            else:
                __import__(module)
                print(f"✓ {module}")
        except ImportError:
            missing.append(module)
            print(f"✗ {module} - MISSING")

    if missing:
        print("\n❌ Missing dependencies!")
        print(f"Install with: pip install {' '.join(missing)}")
        return False

    print("\n✅ All dependencies installed!")
    return True


def check_source_files():
    """Check all source files exist."""
    print("\n" + "=" * 70)
    print("CHECKING SOURCE FILES")
    print("=" * 70)

    required_files = [
        'src/drone_dynamics.py',
        'src/landing_controller.py',
        'src/decision_engine.py',
        'src/path_planner.py',
        'src/energy_ml_model.py',
        'src/vision_terrain_ml.py',
        'src/landing_zone_grid.py',
        'app_gcs.py'
    ]

    missing = []
    for file in required_files:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"✓ {file} ({size:,} bytes)")
        else:
            missing.append(file)
            print(f"✗ {file} - MISSING")

    if missing:
        print("\n❌ Missing source files!")
        return False

    print("\n✅ All source files present!")
    return True


def check_tests():
    """Check test files exist."""
    print("\n" + "=" * 70)
    print("CHECKING TEST FILES")
    print("=" * 70)

    test_files = [
        'tests/test_drone_dynamics.py',
        'tests/test_energy_ml_model.py',
        'tests/test_path_planner.py',
        'tests/test_decision_engine_advanced.py'
    ]

    missing = []
    for file in test_files:
        if os.path.exists(file):
            print(f"✓ {file}")
        else:
            missing.append(file)
            print(f"✗ {file} - MISSING")

    if missing:
        print("\n❌ Missing test files!")
        return False

    print("\n✅ All test files present!")
    return True


def check_documentation():
    """Check documentation files exist."""
    print("\n" + "=" * 70)
    print("CHECKING DOCUMENTATION")
    print("=" * 70)

    doc_files = [
        'GCS_QUICKSTART.md',
        'ML_SYSTEM_DOCUMENTATION.md',
        'IMPLEMENTATION_SUMMARY.md',
        'README_COMPLETE.md'
    ]

    missing = []
    for file in doc_files:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"✓ {file} ({size:,} bytes)")
        else:
            missing.append(file)
            print(f"✗ {file} - MISSING")

    if missing:
        print("\n⚠️  Some documentation missing (non-critical)")
    else:
        print("\n✅ All documentation present!")

    return True


def run_quick_tests():
    """Run quick import tests."""
    print("\n" + "=" * 70)
    print("RUNNING QUICK IMPORT TESTS")
    print("=" * 70)

    try:
        from src.drone_dynamics import DroneDynamics
        print("✓ DroneDynamics imported")

        from src.landing_controller import LandingController
        print("✓ LandingController imported")

        from src.decision_engine import DecisionEngine
        print("✓ DecisionEngine imported")

        from src.path_planner import PathPlanner
        print("✓ PathPlanner imported")

        from src.energy_ml_model import EnergyConfig
        print("✓ EnergyConfig imported")

        from src.vision_terrain_ml import TerrainConfig
        print("✓ TerrainConfig imported")

        print("\n✅ All imports successful!")
        return True

    except Exception as e:
        print(f"\n❌ Import error: {e}")
        return False


def print_summary():
    """Print usage summary."""
    print("\n" + "=" * 70)
    print("QUICK START COMMANDS")
    print("=" * 70)
    print("\n1. Run GCS Dashboard:")
    print("   streamlit run app_gcs.py")
    print("\n2. Run All Tests:")
    print("   pytest tests/ -v")
    print("\n3. Run Specific Test:")
    print("   pytest tests/test_drone_dynamics.py -v")
    print("\n4. Read Documentation:")
    print("   - GCS_QUICKSTART.md (dashboard guide)")
    print("   - ML_SYSTEM_DOCUMENTATION.md (ML components)")
    print("   - IMPLEMENTATION_SUMMARY.md (complete overview)")
    print("\n" + "=" * 70)


def main():
    """Main verification function."""
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║         AUTOLANDRONE SYSTEM VERIFICATION                         ║")
    print("║         ML-Powered Autonomous Landing System                     ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print("\n")

    checks = [
        ("Dependencies", check_dependencies),
        ("Source Files", check_source_files),
        ("Test Files", check_tests),
        ("Documentation", check_documentation),
        ("Quick Imports", run_quick_tests)
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Error during {name} check: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    all_passed = True
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:.<50} {status}")
        if not result:
            all_passed = False

    print("\n" + "=" * 70)

    if all_passed:
        print("✅ ALL CHECKS PASSED - SYSTEM READY!")
        print_summary()
        return 0
    else:
        print("❌ SOME CHECKS FAILED - REVIEW ERRORS ABOVE")
        print("\nTo install missing dependencies:")
        print("pip install streamlit numpy pandas opencv-python-headless scikit-learn plotly pytest")
        return 1


if __name__ == "__main__":
    sys.exit(main())
