import os
import time

import requests
from dotenv import load_dotenv
from terminaltables import AsciiTable


HABR_URL = 'https://career.habr.com/api/frontend/vacancies'
SUPERJOB_URL = 'https://api.superjob.ru/2.0/vacancies/'

HABR_MOSCOW_LOCATION_ID = 'c_678'
SUPERJOB_MOSCOW_TOWN_ID = 4
PROGRAMMING_CATALOGUE_ID = 48
VACANCIES_PER_PAGE = 100

REQUEST_TIMEOUT = 30
RETRY_ATTEMPTS = 5
RETRY_DELAY = 2
REQUEST_DELAY = 0.5

SALARY_FROM_MULTIPLIER = 1.2
SALARY_TO_MULTIPLIER = 0.8

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
        return salary_from * SALARY_FROM_MULTIPLIER

    if salary_to:
        return salary_to * SALARY_TO_MULTIPLIER

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
            'locations[]': HABR_MOSCOW_LOCATION_ID,
            'type': 'all',
            'page': page,
        }

        for attempt in range(RETRY_ATTEMPTS):
            try:
                response = requests.get(
                    HABR_URL,
                    params=params,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                break
            except requests.exceptions.RequestException:
                if attempt == RETRY_ATTEMPTS - 1:
                    raise
                time.sleep(RETRY_DELAY)

        data = response.json()

        if page == 1:
            vacancies_found = data['meta']['totalResults']

        all_vacancies.extend(data['list'])

        total_pages = data['meta']['totalPages']

        if page >= total_pages:
            break

        page += 1
        time.sleep(REQUEST_DELAY)

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
            'town': SUPERJOB_MOSCOW_TOWN_ID,
            'catalogues': PROGRAMMING_CATALOGUE_ID,
            'page': page,
            'count': VACANCIES_PER_PAGE,
        }

        response = requests.get(
            SUPERJOB_URL,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        data = response.json()

        if page == 0:
            vacancies_found = data['total']

        all_vacancies.extend(data['objects'])

        if not data['more']:
            break

        page += 1
        time.sleep(REQUEST_DELAY)

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
    superjob_statistics = get_superjob_statistics(secret_key)

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