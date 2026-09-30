def run(max_steps: int = 5, max_retries: int = 2) -> None:
    retries = 0
    for step in range(1, max_steps + 1):
        print(f"step={step}")
        if step == 1:
            print("observe")
            continue
        if step == 2:
            print("attempt action")
            continue
        if step == 3 and retries < max_retries:
            retries += 1
            print(f"recover/retry ({retries})")
            continue
        print("verify and finish")
        return
    raise RuntimeError("autonomy budget exhausted")

if __name__ == "__main__":
    run()
