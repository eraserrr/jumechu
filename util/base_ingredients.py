import json


def get_base_ingredients():
    with open('document/koreanBasicIngredients.json', 'r') as f:
        data = json.loads(f.read())
    return [x.replace(' ', '') for x in data['한국의 기본 조미료'].split(',')]