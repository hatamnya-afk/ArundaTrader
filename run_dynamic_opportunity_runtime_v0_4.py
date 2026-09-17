
import dynamic_opportunity_boundary_v0_1


if __name__ == "__main__":
    result = dynamic_opportunity_boundary_v0_1.run_controlled()

    print("=" * 100)
    print("ARUNDA DYNAMIC OPPORTUNITY REAL RUNTIME v0.4")
    print("=" * 100)

    if isinstance(result, dict):
        for key, value in result.items():
            print(f"{key}={value}")
    else:
        print(f"RUNTIME_RESULT={result}")