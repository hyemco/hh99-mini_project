import requests
from bs4 import BeautifulSoup

headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
data = requests.get('https://www.fuleaf.com/plants',headers=headers)


soup = BeautifulSoup(data.text, 'html.parser')

main_list = soup.select('#plants_list > ul > div')


for list in main_list:
    main_image = list.select_one('a > div.plant__image').get('style').replace('background-image: url(', '').replace(');', '')
    image = main_image
    title = list.select_one('a > div.plant__title-flex > h3').text

    print(title, image)
