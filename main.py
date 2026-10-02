import os
import time

import requests
from dotenv import load_dotenv
from terminaltables import AsciiTable


HABR_URL = 'https://career.habr.com/api/frontend/vacancies'
SUPERJOB_URL = 'https://api.superjob.ru/2.0/vacancies/'

LANGUAGES = [
    'Python',
    'C',
    'C#',
    'C++',
    'Java',
    'JavaScript',
    'Ruby',
    'Go',
    '1С',
]


def predict_salary(salary_from, salary_to):
    if salary_from and salary_to:
        return (salary_from + salary_to) / 2

    if salary_from:
        return salary_from * 1.2

    if salary_to:
        return salary_to * 0.8

    return None


def predict_rub_salary_habr(vacancy):
    salary = vacancy.get('salary')

    if not salary:
        return None

    if salary.get('currency') != 'RUR':
        return None

    return predict_salary(
        salary.get('from'),
        salary.get('to'),
    )


def predict_rub_salary_for_superJob(vacancy):
    if vacancy.get('currency') != 'rub':
        return None

    return predict_salary(
        vacancy.get('payment_from'),
        vacancy.get('payment_to'),
    )


def fetch_habr_vacancies(language):
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Connection': 'close',
    }

    page = 1
    all_vacancies = []
    vacancies_found = 0

    while True:
        print(f'Habr: {language}, страница {page}')

        params = {
            'q': f'Программист {language}',
            'locations[]': 'c_678',
            'type': 'all',
            'page': page,
        }

        for attempt in range(5):
            try:
                response = requests.get(
                    HABR_URL,
                    params=params,
                    headers=headers,
                    timeout=30,
                )
                response.raise_for_status()
                break
            except requests.exceptions.RequestException:
                if attempt == 4:
                    raise
                time.sleep(2)

        data = response.json()

        if page == 1:
            vacancies_found = data['meta']['totalResults']

        all_vacancies.extend(data['list'])

        total_pages = data['meta']['totalPages']

        if page >= total_pages:
            break

        page += 1
        time.sleep(0.5)

    return vacancies_found, all_vacancies


def get_habr_statistics():
    statistics = {}

    for language in LANGUAGES:
        vacancies_found, vacancies = fetch_habr_vacancies(language)

        salaries = []

        for vacancy in vacancies:
            salary = predict_rub_salary_habr(vacancy)

            if salary is not None:
                salaries.append(salary)

        vacancies_processed = len(salaries)

        if vacancies_processed:
            average_salary = int(
                sum(salaries) / vacancies_processed
            )
        else:
            average_salary = 0

        statistics[language] = {
            'vacancies_found': vacancies_found,
            'vacancies_processed': vacancies_processed,
            'average_salary': average_salary,
        }

    return statistics


def fetch_superjob_vacancies(language, secret_key):
    headers = {
        'X-Api-App-Id': secret_key,
    }

    page = 0
    all_vacancies = []
    vacancies_found = 0

    while True:
        print(f'SuperJob: {language}, страница {page + 1}')

        params = {
            'keyword': f'Программист {language}',
            'town': 4,
            'catalogues': 48,
            'page': page,
            'count': 100,
        }

        response = requests.get(
            SUPERJOB_URL,
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()

        if page == 0:
            vacancies_found = data['total']

        all_vacancies.extend(data['objects'])

        if not data['more']:
            break

        page += 1
        time.sleep(0.5)

    return vacancies_found, all_vacancies


def get_superjob_statistics(secret_key):
    statistics = {}

    for language in LANGUAGES:
        vacancies_found, vacancies = fetch_superjob_vacancies(
            language,
            secret_key,
        )

        salaries = []

        for vacancy in vacancies:
            salary = predict_rub_salary_for_superJob(vacancy)

            if salary is not None:
                salaries.append(salary)

        vacancies_processed = len(salaries)

        if vacancies_processed:
            average_salary = int(
                sum(salaries) / vacancies_processed
            )
        else:
            average_salary = 0

        statistics[language] = {
            'vacancies_found': vacancies_found,
            'vacancies_processed': vacancies_processed,
            'average_salary': average_salary,
        }

    return statistics


def print_statistics_table(statistics, title):
    table_data = [
        [
            'Язык программирования',
            'Вакансий найдено',
            'Вакансий обработано',
            'Средняя зарплата',
        ]
    ]

    for language, language_statistics in statistics.items():
        table_data.append([
            language.lower(),
            language_statistics['vacancies_found'],
            language_statistics['vacancies_processed'],
            language_statistics['average_salary'],
        ])

    table = AsciiTable(table_data, title)

    print()
    print(table.table)


def main():
    load_dotenv()

    secret_key = os.getenv('SUPERJOB_SECRET_KEY')

    habr_statistics = get_habr_statistics()

    superjob_statistics = get_superjob_statistics(
        secret_key,
    )

    print_statistics_table(
        habr_statistics,
        'Habr Moscow',
    )

    print_statistics_table(
        superjob_statistics,
        'SuperJob Moscow',
    )


if __name__ == '__main__':
    main()