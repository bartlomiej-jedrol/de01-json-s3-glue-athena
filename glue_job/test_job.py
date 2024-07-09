from urllib.parse import unquote_plus

print(
    unquote_plus(
        'customer/year%3D2024/month%3D07/day%3D08/2024_07_08+10%3A43%3A27.412_customer.parquet',
        encoding='utf8',
    )
)
