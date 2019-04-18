# LIBS
import re, json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from lxml import html, etree
from operator import itemgetter
import dateparser
import html, sys

# CONFIG
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
requests_timeout = 3


# HELPERS
def xprint(x):
    print(etree.tostring(x, pretty_print=True))

def jprint(arr):
    print(json.dumps(arr, indent=4, sort_keys=False))

def printFunc(s):
    print('#'*100)
    print('AIRBNB LIB:: {}()'.format(s.f_code.co_name))

def request(url):

    print('#'*100)
    print(url)

    # proxy_string = 'http://dmkyod:KfuhLOMHZG@185.47.205.250:24531'
    proxy_string = ''
    proxy = {'http': proxy_string, 'https': proxy_string,}
    req = requests.get(url, headers=headers, proxies=proxy, stream=True, timeout=requests_timeout, verify=False)

    content = req.content.decode('utf-8')

    if not req.status_code == 200:
        print('Error in response')
        # print(content)
        return {
            'error': True,
            'errors': {
                'airbnb_id': 'Error code: {}'.format(req.status_code)
            }
        }


    return content


DEMO = False

# CLASSES

class AIRBNB(object):

    def getApiKey(self, id):
        printFunc(sys._getframe())

        url = 'https://www.airbnb.ru/rooms/{id}'.format(id=id)
        res = request(url)

        print(url)

        # XPATH
        tree = etree.HTML(res)

        content = re.search('{"baseUrl"(.*?)}', res).group(0)
        apiKey = json.loads(content)['key']
        return apiKey

        # dump = tree.xpath('.//meta[@id="_bootstrap-layout-init"]/@content')[0]
        # data = json.loads(dump)
        # apiKey = data['api_config']['key']
        # return apiKey

    class OFFER(object):
        printFunc(sys._getframe())

        def getPrice(self, id, currency):
            url = 'https://www.airbnb.com/api/v2/pdp_listing_booking_details?force_boost_unc_priority_message_type=&guests=1&listing_id={object_id}&show_smart_promotion=0&_format=for_web_dateless&_interaction_type=pageload&_intents=&_p3_impression_id=&number_of_adults=1&number_of_children=0&number_of_infants=0&key={key}&currency={currency}&locale=en'.format(
                object_id=id,
                currency=currency,
                key=AIRBNB().getApiKey(id),
            )
            res = request(url)
            data = json.loads(res)
            price_arr = data['pdp_listing_booking_details'][0]['p3_display_rate']
            response = {
                'currency': currency,
                'amount': price_arr['amount']
            }
            return response


        def get(self, id):


            url = 'https://airbnb.com/rooms/{id}'.format(id=id)

            if DEMO:
                res = open('tmp.txt', 'r').read()

            else:
                res = request(url)
                with open('tmp.txt', 'w') as out_file:
                    out_file.write(res)

            # CHECK OFFER EXISTING
            checker = etree.HTML(res).xpath('.//link[@rel="canonical"]/@href')
            checker = checker[0] if checker else False
            if checker and checker == 'https://www.airbnb.com/':
                return {
                    'error': True,
                    'errors': {
                        'airbnb_id': 'Offer not found'
                    }
                }

            # CHECK IF IP IS BANNED
            has_title = etree.HTML(res).xpath('.//title/text()')
            has_title = has_title[0] if has_title else False
            if not has_title:
                return {
                    'error': True,
                    'errors': {
                        'airbnb_id': 'Proxy is banned'
                    }
                }

            # IF STATUS CODE IS ERROR
            if type(res) == dict and 'error' in res:
                return res  # False if offer not found in airbnb page


            content = False
            for r in res.splitlines():
                if '"bootstrapData"' in r:

                    content = re.search('<!--{"behavioralUid"(.*?)-->', res).group(0)
                    content = re.search('<!--(.*?)-->', content).group(1)
                    content = json.loads(content)
                    break

                    # content = re.search('<!--(.*?)-->', r).group(1)
                    # content = json.loads(content)
                    # break

            if not content:
                return 'Offer not found'



            listingInfo = content['bootstrapData']['reduxData']['homePDP']['listingInfo']['listing']
            listingExtra = listingInfo['p3_event_data_logging']


            # http://jsonviewer.stack.hu/
            # jprint(listingInfo)



            # GET PRICE
            price = self.getPrice(id=id, currency=listingInfo['native_currency'])

            # tree = etree.HTML(res)
            # price = tree.xpath('.//meta[@name="description"]/@content')[0]
            # price = re.search('\s€(\w+).\s', price)
            # if price:
            #     price = price.group(1)
            # else:
            #     price = False

            # print("PRICE" ,price)



            # AMENTIES
            amenties_arr = []
            listing_amenities = [{'id': c['id'], 'name': c['name'], 'tag': c['tag']} for c in listingInfo['listing_amenities']]
            for c in listingInfo['see_all_amenity_sections']:
                def getAmenties(id):
                    for c in listing_amenities:
                        if c['id'] == id:
                            return c
                if not c['title'] == 'Not included':
                    amenties_arr.append({'group': c['title'], 'items': [getAmenties(a) for a in c['amenity_ids']]})

            # PHOTOS
            photos_arr = [{'src': c['xx_large'], 'index': c['sort_order']} for c in listingInfo['photos']]
            photos_arr = [{'src': c['src'], 'index': c['index']} for c in sorted(photos_arr, key=itemgetter('index'), reverse=False)]

            # DESCRIPTION
            description = listingInfo['sectioned_description']
            description_text = ''
            description_html = ''
            if description['description']:
                description_text = html.unescape(description['description'])
                description_html = description_text.replace('\r','<br />').replace('\n','<br />')
            description = {
                'text': description_text,
                'html': description_html,
                'lang': description['localized_language_name'],
            }
            # print(description)

            results = {
                'id': listingInfo['id'],
                'price': price,
                'name': html.unescape(listingInfo['name']),
                'bathroom_label': listingInfo['bathroom_label'],
                'bed_label': listingInfo['bed_label'],
                'bedroom_label': listingInfo['bedroom_label'],
                'guest_label': listingInfo['guest_label'],
                # 'person_capacity': listingInfo['person_capacity'],
                'star_rating': listingInfo['star_rating'],
                'calendar_last_updated_at': listingInfo['calendar_last_updated_at'],
                'min_nights': listingInfo['min_nights'],
                'location_title': listingInfo['location_title'],
                'lat': listingInfo['lat'],
                'lng': listingInfo['lng'],
                'room_and_property_type': listingInfo['room_and_property_type'],
                'room_type_category': listingInfo['room_type_category'],
                'guest_controls': {i: c for i,c in listingInfo['guest_controls'].items() if 'allows_' in i},
                'photos': photos_arr,
                'description': description,
                'primary_host': listingInfo['primary_host'],
                'amenties': amenties_arr,
                # 'listing_amenities': listing_amenities,

                'check_in': listingInfo['localized_check_in_time_window'],
                'check_out': listingInfo['localized_check_out_time'],

                # EXTRA...
                'description_language': listingExtra['description_language'],
                'is_superhost': listingExtra['is_superhost'],
                'home_tier': listingExtra['home_tier'],

                'checkin_rating': listingExtra['checkin_rating'],
                'cleanliness_rating': listingExtra['cleanliness_rating'],
                'communication_rating': listingExtra['communication_rating'],
                'location_rating': listingExtra['location_rating'],
                'accuracy_rating': listingExtra['accuracy_rating'],
                'value_rating': listingExtra['value_rating'],

                # '': listingInfo[''],

            }
            # jprint(results)
            return results



            # XPATH
            # tree = etree.HTML(res)
            # title = tree.xpath('.//div[@id="summary"]//h1/span/text()')[0]
            # location = tree.xpath('.//div[@id="summary"]//a[@href="#neighborhood"]/div/text()')[0]
            # variant = tree.xpath('.//div[@id="summary"]//a[starts-with(@href,"/s/")]/div/span/span/span/text()')[0]
            # options = tree.xpath('.//div[@id="summary"]/following-sibling::div/div/div/div/div/div/div/span[string-length(text()) > 3]/text()')
            #
            # results = {
            #     'title': title,
            #     'location': location,
            #     'variant': variant,
            #     'options': options,
            # }
            # print(results)


    # class FEEDBACKS2(object):
    #
    #     def get(self, id):
    #         url = 'https://www.airbnb.com/users/show/{id}'.format(id=id)
    #
    #         # res = request(url)
    #
    #         # with open('feedbacks.txt', 'w') as out_file:
    #         #     out_file.write(res)
    #
    #         res = open('feedbacks.txt', 'r').read()
    #
    #         # SOUP
    #         soup = BeautifulSoup(res, "lxml")
    #
    #         rows = soup.find('div',{'class': 'reviews'}).find_all('div',id=re.compile("review-"))
    #
    #         results_arr = []
    #         for r in rows:
    #             text = r.find('div',{'class':'expandable-content'}).find('p').text
    #             country = r.find('a',{'class':'link-reset'})
    #             date = r.find('span',{'class':'text-muted date'})
    #             author_name = r.find('div',{'class':'profile-name'}).text
    #             author_img = r.find('div',{'class','media-photo'}).find('img').get('src')
    #             airbnb_offer_id = r.find('div',{'class':'avatar-wrapper'}).find('a').get('href').split('/')[-1]
    #
    #             answer = r.find('div',{'class':'media'})
    #             if answer:
    #                 answer = answer.find('div',{'class':'media-body'}).find('p').text
    #             else:
    #                 answer = False
    #
    #
    #             results_arr.append({
    #                 'text': text,
    #                 'date': date.text if date else False,
    #                 'country': country.text if country else False,
    #                 'airbnb_offer_id': airbnb_offer_id,
    #                 'author_name': author_name,
    #                 'author_img': author_img,
    #                 'answer': answer
    #             })
    #
    #         jprint(results_arr)
    #
    #
    #         # print(data_row)


    class FEEDBACKS(object):
        printFunc(sys._getframe())

        def get_count(self, id):
            url = 'https://www.airbnb.com/api/v2/reviews?key={key}&currency=EUR&locale=en&listing_id={listing_id}&role=guest&_format=for_p3&_limit={limit}&_offset={offset}&_order=combined_ranker_v1'.format(
                key=AIRBNB().getApiKey(id),
                listing_id=id,
                limit=1,
                offset=0,
            )
            res = request(url)
            data = json.loads(res)
            reviews_count = int(data['metadata']['reviews_count'])
            return reviews_count

        def get(self, id):

            apikey = AIRBNB().getApiKey(id)
            reviews_count = AIRBNB().FEEDBACKS().get_count(id=id)
            limit = 100

            def getOffset(offset=0):

                url = 'https://www.airbnb.com/api/v2/reviews?key={key}&currency=EUR&locale=en&listing_id={listing_id}&role=guest&_format=for_p3&_limit={limit}&_offset={offset}&_order=combined_ranker_v1'.format(
                    key = apikey,
                    listing_id = id,
                    limit = limit,
                    offset = offset,
                )
                res = request(url)
                data = json.loads(res)
                return data


            # if not reviews_count:
            #     data = getOffset()
            #     reviews_count = int(data['metadata']['reviews_count'])
            #     limit = 100


            # print(limit, reviews_count)

            results_arr = []
            for r in range(0, reviews_count, limit):
                print('STEP: {}'.format(r))
                data = getOffset(offset=r)
                for r in data['reviews']:

                    v = {
                        'text': r['comments'],
                        'airbnbn_feedback_id': r['id'],
                        'created_at': dateparser.parse(r['created_at']),
                        'rating': r['rating'],
                        'answer': r['response'],
                        'airbnb_author_id': r['reviewer']['id'],
                        'author_first_name': r['reviewer']['first_name'],
                        'author_avatar': r['reviewer']['picture_url'],

                    }
                    results_arr.append(v)

            # jprint(results_arr)
            # print(len(results_arr))

            # jprint(data)
            return results_arr


    class CALENDAR(object):
        printFunc(sys._getframe())

        def get(self, id):
            url = 'https://www.airbnb.ru/api/v2/calendar_months?_format=with_conditions&count={count}&listing_id={object_id}&month={months}&year={year}&key={key}&currency=EUR&locale=en'.format(
                object_id=id,
                year=datetime.now(),
                count=24,
                months=24,
                key=AIRBNB().getApiKey(id),
            )

            res = request(url)
            data = json.loads(res)

            items_arr = []
            for d in data['calendar_months']:

                for day in d['days']:
                    item = {
                        'available': day['available'],
                        # 'date': dateparser.parse(day['date']),
                        'date_string': day['date'],
                    }
                    items_arr.append(item)


            print('RECEIVED DATES: {}'.format(len(items_arr)))
            return items_arr



if __name__ == "__main__":
    pass

    s = AIRBNB().OFFER().get(id=30528072)
    print(s)
    # AIRBNB().CALENDAR().get(id=22272483)
    # AIRBNB().FEEDBACKS().get(id=6089759)
    # AIRBNB().FEEDBACKS().get_count(id=6089759)
