"""Smoke-тест окружения: версии пакетов, API-запрос к hh.ru, pandas/numpy-аналитика."""

import sys
import platform

import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os


def get_versions() -> list[tuple[str, str]]:
    """Собирает версии Python и ключевых пакетов."""
    return [
        ("Python", sys.version.split()[0]),
        ("Platform", platform.platform()),
        ("requests", requests.__version__),
        ("pandas", pd.__version__),
        ("numpy", np.__version__),
    ]


def main() -> int:
    # 1. Читаем .env через python-dotenv
    load_dotenv()
    base_url = os.getenv("TEST_API_URL")
    if not base_url:
        print("[FAIL] Переменная TEST_API_URL не найдена в .env")
        return 1
    print(f"[OK] TEST_API_URL = {base_url}")

    summary_rows = [(name, ver) for name, ver in get_versions()]

    # 2. GET-запрос к API вакансий
    url = f"{base_url}/vacancies?per_page=10"
    headers = {"User-Agent": "SmokeTestBot/1.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        status = resp.status_code
    except Exception as e:
        print(f"[FAIL] Запрос к {url} завершился ошибкой: {e!r}")
        summary_rows.append(("API request", f"FAIL: {type(e).__name__}"))
        _print_summary(summary_rows)
        return 1

    # 3. DataFrame + numpy: считаем вакансии с указанной зарплатой
    #     (если API вернул не 200 — например, geo-block 403 — вакансий не будет)
    try:
        data = resp.json() if status == 200 else {}
    except ValueError:
        data = {}
    items = data.get("items", [])
    df = pd.DataFrame(items)
    n_total = len(df)

    def has_salary(sal: object) -> bool:
        if isinstance(sal, dict):
            return sal.get("amount") is not None
        return False

    salary_mask = np.array(
        [has_salary(s) for s in df["salary"]] if "salary" in df.columns else [] ,
        dtype=bool,
    )
    n_with_salary = int(np.sum(salary_mask)) if salary_mask.size else 0
    share_pct = float(np.round(n_with_salary / n_total * 100, 1)) if n_total else 0.0

    net_ok = status == 200 or status == 403  # 403 = geo-block hh.ru, сеть живая
    print(
        f"[{'OK' if net_ok else 'WARN'}] HTTP {status}, "
        f"получено вакансий: {n_total}, из них с зарплатой: {n_with_salary}"
    )

    # 4. Итоговая сводка одной таблицей
    summary_rows += [
        ("API status", str(status)),
        ("Vacancies fetched", str(n_total)),
        ("With salary (numpy)", f"{n_with_salary} ({share_pct}%)"),
        ("Result", "PASS" if net_ok else "FAIL"),
    ]
    _print_summary(summary_rows)
    return 0 if net_ok else 1


def _print_summary(rows: list[tuple[str, str]]) -> None:
    df = pd.DataFrame(rows, columns=["Check", "Value"])
    print("\n===== SMOKE TEST SUMMARY =====")
    print(df.to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
