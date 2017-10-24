
# coding: utf-8

# In[1]:

import json
import datetime
import csv
import time

try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request    


# In[2]:

#Loading the requirements
app_id = '305779013219420'
app_secret = 'a2e645d4a503f2e2326ced754d21e50f'
#page_id = 'urbanladder'

access_token = app_id + '|' + app_secret
access_token


# In[3]:

#connecting to facebook
def requestData(url):
    req = Request(url)
    success = False
    while success is False:
        try:
            response = urlopen(req)
            if response.getcode() == 200:
                success = True
        except Exception as e:
            print(e)
            time.sleep(5)
            
            print('Error in URL {}: {}'.format(url ,datetime.datetime.now))
            print('Retrying.')
    return response.read()

#let's handle the unicode and decoding problems
def unicode_decode(text):
    try:
        return text.encode('utf-8').decode()
    except UnicodeDecodeError:
        return text.encode('utf-8').decode()


def getFbPagecomments(base_url):
    #constructing the url string
    fields = '&fields=id,message,reactions.limit(0).summary(true)' +         ",created_time,comments,from,attachment"
    url = base_url + fields
    
    return url

def getReactionsForComments(base_url):

    reaction_types = ['like', 'love', 'wow', 'haha', 'sad', 'angry']
    reactions_dict = {}   # dict of {status_id: tuple<6>}

    for reaction_type in reaction_types:
        fields = "&fields=reactions.type({}).limit(0).summary(total_count)".format(
            reaction_type.upper())

        url = base_url + fields

        data = json.loads(requestData(url))['data']

        data_processed = set()  # set() removes rare duplicates in statuses
        for status in data:
            id = status['id']
            count = status['reactions']['summary']['total_count']
            data_processed.add((id, count))

        for id, count in data_processed:
            if id in reactions_dict:
                reactions_dict[id] = reactions_dict[id] + (count,)
            else:
                reactions_dict[id] = (count,)

    return reactions_dict

def commentProcessing(comment, status_id,parent_id=''):
    #The post data might have comments or do not have comments
    comment_id = comment['id']
    comment_message = ''if 'message' not in comment or comment['message']         is '' else unicode_decode(comment['message'])
    comment_author = unicode_decode(comment['from']['name'])
    number_reactions = 0 if'reactions' not in comment else         comment['reactions']['summary']['total_count']
       
    if 'attachment' in comment:
        attachment_type = comment['attachment']['type']
        attachment_type = 'gif' if attachment_type =='animated_image_share'             else attachment_type
        attach_tag = "[[{}]]".format(attachment_type.upper())
        comment_message = attach_tag if comment_message is '' else             comment_message + " " + attach_tag
    
   #time is of the essence here so let's make it in our sense
    comment_published = datetime.datetime.strptime(
        comment['created_time'], '%Y-%m-%dT%H:%M:%S+0000')
    comment_published = comment_published + datetime.timedelta(hours=+5)# IST
    comment_published = comment_published.strftime('%Y-%m-%d %H:%M:%S') # best time format for spreadsheet programs
    
    #let's return the tuple of all the processed data
    return (comment_id, status_id, parent_id, comment_message, comment_author,
            comment_published)



# In[4]:

def fbPageFeedComments(page_id, access_token):
    with open('{}_facebook_comments.csv'.format(page_id), 'w') as file:
        w = csv.writer(file)
        w.writerow(["comment_id", "status_id", "parent_id", "comment_message",
                    "comment_author", "comment_published"])
        num_processed = 0
        scrape_starttime = datetime.datetime.now()
        after = ''
        base = "https://graph.facebook.com/v2.10"
        parameters = "?limit={}&access_token={}".format(100, access_token)
        
        print("Scraping {} Comments From Posts: {}\n".format(page_id, scrape_starttime))
        
        with open('{}_facebook_statuses.csv'.format(page_id), 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for status in reader:
                has_next_page = True
                
                while has_next_page:
                    
                    node = "/{}/comments".format(status['status_id'])
                    after = '' if after is '' else "&after={}".format(after)
                    base_url = base + node + parameters + after
                    url = getFbPagecomments(base_url)
                    comments = json.loads(requestData(url))
                   #reactions = getReactionsForComments(base_url)
                    for comment in comments['data']:
                        comment_data = commentProcessing(comment, status['status_id'])
                        #eactions_data = reactions[comment_data[0]]
                        
                        # calculate thankful/pride through algebra
                      #num_special = comment_data[6] - sum(reactions_data)
                        w.writerow(comment_data,)
                        
                        if 'comments' in comment:
                            has_next_subpage = True
                            sub_after = ''
                            
                            while has_next_subpage:
                                sub_node = "/{}/comments".format(comment["id"])
                                sub_after = '' if sub_after is '' else "&after={}".format(sub_after)
                                sub_base_url = base + sub_node + parameters + sub_after
                                sub_url = getFbPagecomments(
                                    sub_base_url)
                                print(sub_url)
                                sub_comments = json.loads(requestData(sub_url))
                               #sub_reactions = getReactionsForComments(sub_base_url)
                                for sub_comment in sub_comments['data']:
                                    sub_comment_data = commentProcessing(
                                        sub_comment, status['status_id'], comment['id'])
                                  # sub_reactions_data = sub_reactions[
                                  #     sub_comment_data[0]]
                                  # num_sub_special = sub_comment_data[6] - sum(sub_reactions_data)
                                    w.writerow(sub_comment_data)
                                    
                                    num_processed += 1
                                    if num_processed % 100 == 0:
                                        print("{} Comments Processed: {}".format(
                                            num_processed,
                                            datetime.datetime.now()))

                                if 'paging' in sub_comments:
                                    if 'next' in sub_comments['paging']:
                                        sub_after = sub_comments[
                                            'paging']['cursors']['after']
                                    else:
                                        has_next_subpage = False
                                else:
                                    has_next_subpage = False


                        # Now we're in the battle ground let's have some comment fun
                        num_processed += 1
                        if num_processed % 100 == 0:
                            print("{} Comments Processed: {}".format(
                                num_processed, datetime.datetime.now()))


                    if 'paging' in comments:
                        if 'next' in comments['paging']:
                            after = comments['paging']['cursors']['after']
                        else:
                            has_next_page = False
                    else:
                        has_next_page = False

        print("\nDone!\n{} Comments Processed in {}".format(
            num_processed, datetime.datetime.now() - scrape_starttime))


# In[5]:

# fbPageFeedComments("slimjim", access_token)


# In[ ]:



