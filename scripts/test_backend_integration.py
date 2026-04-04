#!/usr/bin/env python3
"""Test full backend integration: Ollama + XGBoost + Gemma4."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_ollama_connection():
    """Test Ollama connection."""
    print("\n1. Testing Ollama connection...")
    from src.rl.ollama_client import OllamaClient

    ollama = OllamaClient()
    health = ollama.check_health()

    print(f"   Status: {health['status']}")
    print(f"   Models: {health.get('available_models', [])}")
    print(f"   Required model: {health.get('required_model')}")
    print(f"   Model available: {health.get('model_available', False)}")

    if health['status'] != 'healthy':
        print("   ERROR: Ollama is not healthy!")
        return False

    # Test simple generation
    try:
        response = ollama.generate("Say 'test successful' in one word.")
        print(f"   Test generation: {response.strip()[:50]}...")
        print("   Ollama connection: OK")
        return True
    except Exception as e:
        print(f"   ERROR: {e}")
        return False


def test_xgboost_training():
    """Test XGBoost training on Qdrant data."""
    print("\n2. Testing XGBoost training...")
    from src.ml.xgboost_trainer import XGBoostTrainer

    trainer = XGBoostTrainer()

    try:
        # Train model for GOLD
        print("   Training GOLD model...")
        model = trainer.train_model("GOLD", target_horizon=7, force_retrain=False)
        print(f"   Model trained: {model is not None}")

        # Get feature importance
        importance = trainer.get_feature_importance("GOLD", top_n=10)
        print(f"   Feature importance: {len(importance)} features")
        print("   Top 5 features:")
        for feat, imp in list(importance.items())[:5]:
            print(f"      {feat}: {imp:.4f}")

        # Train OIL model
        print("   Training OIL model...")
        model = trainer.train_model("OIL", target_horizon=7, force_retrain=False)
        print(f"   Model trained: {model is not None}")

        print("   XGBoost training: OK")
        return True
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prediction_service():
    """Test prediction service with XGBoost + Gemma4."""
    print("\n3. Testing prediction service...")
    from src.ml.prediction_service import PredictionService

    service = PredictionService(confidence_threshold=0.6)

    try:
        # Test prediction for GOLD
        print("   Predicting GOLD...")
        result = service.predict("GOLD", target_horizon=7)

        print(f"   XGBoost prediction: {result['xgboost_prediction']:+.2f}%")
        print(f"   XGBoost confidence: {result['xgboost_confidence']:.2f}")
        print(f"   Final confidence: {result['final_confidence']:.2f}")
        print(f"   Recommendation: {result['recommendation']}")

        if result['gemma4_analysis']:
            print(f"   Gemma4 triggered: YES")
            analysis = result['gemma4_analysis']
            print(f"   Gemma4 confidence: {analysis.get('confidence', 0):.2f}")
            print(f"   Gemma4 conclusion: {analysis.get('conclusion', 'N/A')[:80]}...")
        else:
            print(f"   Gemma4 triggered: NO (high confidence)")

        # Test prediction for OIL
        print("\n   Predicting OIL...")
        result = service.predict("OIL", target_horizon=7)
        print(f"   XGBoost prediction: {result['xgboost_prediction']:+.2f}%")
        print(f"   Confidence: {result['final_confidence']:.2f}")
        print(f"   Recommendation: {result['recommendation']}")

        print("   Prediction service: OK")
        return True
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_prediction():
    """Test batch prediction."""
    print("\n4. Testing batch prediction...")
    from src.ml.prediction_service import PredictionService

    service = PredictionService()

    try:
        results = service.batch_predict(["GOLD", "OIL"], target_horizon=7)

        print("   Batch results:")
        for result in results:
            print(f"      {result['commodity']}: {result['xgboost_prediction']:+.2f}% "
                  f"(conf: {result['final_confidence']:.2f})")

        print("   Batch prediction: OK")
        return True
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_explainable_predictions():
    """Test XGBoost explanations with Gemma4 validation."""
    print("\n5. Testing explainable predictions with Gemma4 validation...")
    from src.ml.prediction_service import PredictionService
    from src.ml.presentation import format_prediction_for_public

    service = PredictionService()

    try:
        # Test explainable prediction for GOLD
        print("   Testing explainable prediction for GOLD...")
        result = service.predict_with_validation("GOLD", target_horizon=7)

        print(f"\n   XGBoost Prediction: {result['xgboost']['prediction_pct']:+.2f}%")
        print(f"   Confidence: {result['xgboost']['confidence']:.0%}")

        print("\n   Top 3 Features:")
        for i, feat in enumerate(result['xgboost']['top_features'], 1):
            print(f"      {i}. {feat['name']}: {feat['value']:.4f}")
            print(f"         {feat['correlation'][:60]}...")
            print(f"         [Importance: {feat['importance']:.1%}, Impact: {feat['impact']}]")

        print(f"\n   XGBoost Reasoning: {result['xgboost']['reasoning'][:100]}...")

        # Gemma4 validation
        gemma4 = result['gemma4_validation']
        print(f"\n   Gemma4 Validation:")
        print(f"      Agreement: {gemma4['agreement']:.0%}")
        print(f"      Valid: {gemma4.get('valid', 'N/A')}")
        if gemma4.get('critique'):
            print(f"      Critique: {gemma4['critique'][:80]}...")

        print(f"\n   Final Recommendation: {result['final_recommendation']}")

        # Show public presentation format
        print("\n   --- Public Presentation Format ---")
        public_format = format_prediction_for_public(result)
        # Print first 800 chars
        print(public_format[:800])
        print("   ... [truncated for display] ...")

        print("\n   Explainable predictions: OK")
        return True
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    print("=" * 70)
    print("Backend Integration Test")
    print("=" * 70)
    print("\nTesting: Ollama + XGBoost + Gemma4 integration")

    results = []

    # Run tests
    results.append(("Ollama Connection", test_ollama_connection()))
    results.append(("XGBoost Training", test_xgboost_training()))
    results.append(("Prediction Service", test_prediction_service()))
    results.append(("Batch Prediction", test_batch_prediction()))
    results.append(("Explainable Predictions", test_explainable_predictions()))

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")

    all_passed = all(passed for _, passed in results)

    print("\n" + "=" * 70)
    if all_passed:
        print("All tests PASSED!")
    else:
        print("Some tests FAILED!")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
