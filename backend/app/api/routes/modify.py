with open('tracking.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'rent_inv = (lucro_operacional / vgv_vendido) * 100 if vgv_vendido > 0 else 0.0',
    'rent_inv = (lucro_operacional / abs(exposicao_maxima)) * 100 if exposicao_maxima and exposicao_maxima != 0 else 0.0'
)

content = content.replace(
    'rent_inv = (combined_actuals["lucro_liq_operacional"] / combined_actuals["receita_bruta"]) * 100 if combined_actuals["receita_bruta"] > 0 else 0.0',
    'rent_inv = (combined_actuals["lucro_liq_operacional"] / abs(combined_actuals.get("exposicao_maxima", 0.0))) * 100 if combined_actuals.get("exposicao_maxima", 0.0) != 0 else 0.0'
)

with open('tracking.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Replaced')
