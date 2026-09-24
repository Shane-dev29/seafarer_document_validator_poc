from bs4 import BeautifulSoup

with open('coc_search_dump.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'html.parser')

forms = soup.find_all('form')
print(f"Total Forms found: {len(forms)}")

for idx, form in enumerate(forms, 1):
    print(f"\n================ Form {idx} ================")
    print(f"Name   : {form.get('name')}")
    print(f"Action : {form.get('action')}")
    print(f"Method : {form.get('method')}")
    print("-" * 50)

    elements = form.find_all(['input', 'select', 'textarea', 'button'])
    for el in elements:
        tag = el.name
        el_type = el.get('type', tag)
        name = el.get('name', '')
        el_id = el.get('id', '')
        val = el.get('value', '')

        # Label detection logic:
        label = ''
        parent_td = el.find_parent('td')
        if parent_td:
            # Often labels are in the preceding <td> in table layouts
            prev_td = parent_td.find_previous_sibling('td')
            if prev_td:
                label = prev_td.get_text(strip=True).replace('*', '').replace(':', '')
        if not label and el_id:
            lbl = soup.find('label', {'for': el_id})
            if lbl:
                label = lbl.get_text(strip=True)

        print(f"<{tag}> Type: {el_type:<10} | Name: {name:<20} | ID: {el_id:<15} | Value: {val:<10} | Label: {label}")
