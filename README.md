# Python Shopware

Very simple helpers to work with the Shopware API.

## Example

```python
#!/usr/bin/env python3

import shopware

ACCESS_KEY_ID = 'SWIxxxxx'
ACCESS_KEY_SECRET = 'xxxxx'
SHOP_URL = 'https://xxxxx'

client = shopware.ApiClient(SHOP_URL, key_id=ACCESS_KEY_ID, key_secret=ACCESS_KEY_SECRET)

orders = shopware.parse_api_response(client.call('search/order', data={
    'associations': {
        'lineItems': {
            'sort': [{
                'field': 'position',
                'order': 'asc',
            }],
        }
    },
    'filter': [
        {
            'field': 'orderNumber',
            'type': 'equals',
            'value': 12345,
        },
    ],
}))

for order in orders:
    for line_item in order['lineItems']:
        print(line_item['label'], line_item['position'])
```
