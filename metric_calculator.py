__author__ = 'jorgesaldivar'

from dateutil import parser

import csv
import datetime
import json
import numpy
import sys


###
# Data for metric: response time of comments
#
# Compute the time that passes between
# the creation of a comment and its
# first reply
#
###
def data_metric_response_time_comments(idea):
    ignored_comments, problematic_comments = 0, 0
    vec_comments, attended_comments = {}, []

    for comment in idea['comments_array']:
        if comment['parent_type'] == 'idea':
            try:
                vec_comments[comment['id']]['creation_dt'] = parser.parse(comment['creation_datetime'])
            except KeyError:
                vec_comments[comment['id']] = {'creation_dt': parser.parse(comment['creation_datetime']),
                                               'replies': []}
        else:
            # found a reply, save
            try:
                vec_comments[comment['parent_id']]['replies'].append(comment)
            except KeyError:
                vec_comments[comment['parent_id']] = {'creation_dt': '', 'replies': [comment]}

    for comment_id, comment in vec_comments.iteritems():
        if len(comment['replies']) > 0:
            first_reaction = sort_elements_chronologically(comment['replies'])[0]
            response_time = first_reaction - comment['creation_dt']
            if response_time.total_seconds() < 0:
                problematic_comments += 1
                response_time_hours = -999
            else:
                response_time_hours = response_time.total_seconds() / 3600
            first_reaction_dt = first_reaction.strftime('%Y-%m-%d %H:%M:%S%z')
            attended_comments.append({'comment_id': comment_id,
                                      'comment_dt': comment['creation_dt'].strftime('%Y-%m-%d %H:%M:%S%z'),
                                      'first_reaction_dt': first_reaction_dt,
                                      'response_time_hours': response_time_hours})
        else:
            ignored_comments += 1

    return ignored_comments, problematic_comments, attended_comments


####
# Data for metric: response time of ideas
#
# Compute the time that passes between
# the creation of an idea and its first response
# (vote or comment)
#
# Assumption: Ignores no replied ideas
#
# If we talk about community responsiveness
# communities should be penalized for their
# no replied ideas
#
####
def sort_elements_chronologically(elements):
    elements_dt = []

    for element in elements:
        elements_dt.append(parser.parse(element['creation_datetime']))

    return sorted(elements_dt)


def data_metric_response_time_idea(idea):
    # uncompleted_idea means don't have in the data set info about all
    # the idea's votes and comments
    problematic_idea, uncompleted_idea = 0, 0
    first_reaction_comment, first_reaction_vote = 0, 0
    first_reaction_dt, response_time_hours = '', 0

    idea_creation_time = parser.parse(idea['creation_datetime'])
    num_comments = int(idea['comments'])
    num_votes = int(idea['up_votes']) + int(idea['down_votes'])
    comments_sorted, votes_sorted = None, None

    if num_comments == 0 and num_votes == 0:
        response_time_hours = -999
    else:
        if len(idea['comments_array']) == num_comments and \
           len(idea['votes_array']) == num_votes:
            if num_comments > 0:
                comments_sorted = sort_elements_chronologically(idea['comments_array'])
            if num_votes > 0:
                votes_sorted = sort_elements_chronologically(idea['votes_array'])
            if comments_sorted:
                if votes_sorted:
                    if comments_sorted[0] > votes_sorted[0]:  # '>' means which is newer
                        first_reaction = votes_sorted[0]
                        type_first_reaction = 'vote'
                    else:
                        first_reaction = comments_sorted[0]
                        type_first_reaction = 'comment'
                else:
                    first_reaction = comments_sorted[0]
                    type_first_reaction = 'comment'
            else:
                first_reaction = votes_sorted[0]
                type_first_reaction = 'vote'
            response_time = first_reaction - idea_creation_time
            if response_time.total_seconds() < 0:
                problematic_idea = 1
                response_time_hours = -999
            else:
                response_time_hours = response_time.total_seconds() / 3600
                if type_first_reaction == 'comment':
                    first_reaction_comment = 1
                else:
                    first_reaction_vote = 1
            first_reaction_dt = first_reaction.strftime('%Y-%m-%d %H:%M:%S%z')
        else:
            uncompleted_idea = 1
            response_time_hours = -999

    return response_time_hours, problematic_idea, first_reaction_comment, \
           first_reaction_vote, first_reaction_dt, uncompleted_idea


####
# Data for metric: comments voted and replied
#
# Compute the number of votes (positive and negatives)
# and replies that the comments received
#
####
def data_metric_number_votes_replies_comments(idea):
    comments_voted, comments_p_voted, comments_n_voted = 0, 0, 0
    replies, replies_voted, replies_p_voted, replies_n_voted = 0, 0, 0, 0
    replies_replied, comments = 0, 0

    for comment in idea['comments_array']:
        if comment['parent_type'] == 'idea':
            comments += 1
            if comment['up_votes'] != '0' or comment['down_votes'] != '0':
                comments_voted += 1
                if comment['up_votes'] != '0':
                    comments_p_voted += 1
                else:
                    comments_n_voted += 1
        else:
            replies += 1
            if comment['up_votes'] != '0' or comment['down_votes'] != '0':
                replies_voted += 1
                if comment['up_votes'] != '0':
                    replies_p_voted += 1
                else:
                    replies_n_voted += 1
            if comment['replies'] != '0':
                replies_replied += 1

    return comments, comments_voted, comments_p_voted, comments_n_voted, replies, replies_voted, \
           replies_p_voted, replies_n_voted, replies_replied


####
# Data for metric: ideas voted and commented
#
# Compute the number of votes (positive and negatives)
# and comments that ideas received
#
####
def data_metric_number_votes_comments_idea(idea):
    idea_commented, idea_voted, idea_p_voted, idea_n_voted = 0, 0, 0, 0
    ignored_idea, attended_idea, idea_only_voted, idea_only_commented = 0, 0, 0, 0
    idea_voted_commented = 0

    if idea['up_votes'] != '0' or idea['down_votes'] != '0':
        idea_voted = 1
        if idea['up_votes'] != '0':
            idea_p_voted = 1
        if idea['down_votes'] != '0':
            idea_n_voted = 1
    if idea['comments'] != '0':
        idea_commented = 1
    if idea_voted == 0 and idea_commented == 0:
        ignored_idea = 1
    else:
        attended_idea = 1
        if idea_voted == 0 and idea_commented == 1:
            idea_only_commented = 1
        elif idea_voted == 1 and idea_commented == 0:
            idea_only_voted = 1
        else:
            idea_voted_commented = 1

    return idea_voted, idea_p_voted, idea_n_voted, idea_commented, ignored_idea, attended_idea, \
           idea_only_voted, idea_only_commented, idea_voted_commented


###
# Data for metric: irrelevant ideas
#
# Check whether idea was classified as irrelevant
# (off-topic or recycle bin)
#
####
def data_metric_irrelevant_idea(idea):
    if idea['status'] == 'offtopic' or idea['status'] == 'recyclebin':
        return 1
    else:
        return 0


###
# Data metric: feedback on Newcomer Ideas
#
# Compute the number of times ideas
# posted by newcomers were answered
#
###
def created_by_newcomer(idea, authors):
    newcomer_time_window = 5  # 5 days

    # Identify whether an idea was created by someone who has
    # registered within the last newcomer_time_window days

    try:
        idea_author = authors[idea['author_id']]
        author_registration_time = parser.parse(idea_author['registration_datetime'])
        idea_creation_time = parser.parse(idea['creation_datetime'])
        diff = author_registration_time - idea_creation_time
        # If the time between the registration and the creation of the idea is equal or
        # less than the defined newcomer time window, the author can be considered a
        # newcomer
        if diff.days <= newcomer_time_window:
            return {'isnewcomer': True, 'explanation': ''}
        else:
            if diff.days < 0:
                return {'isnewcomer': False, 'explanation': 'Wrong_registration_date'}
            else:
                return {'isnewcomer': False, 'explanation': 'No_newcomer'}
    except KeyError:
        return {'isnewcomer': False, 'explanation': 'Unknown_registration_date'}


def data_metric_feedback_newcomer_idea(idea, authors):
    idea_by_newcomer, received_feedback = 0, 0
    type_first_feedback, first_feedback_dt = '', ''
    response_time_hours = -999

    idea_creator = created_by_newcomer(idea, authors)
    if idea_creator['isnewcomer']:
        idea_by_newcomer = 1
        response_time_hours, problematic_idea, first_react_comment, first_react_vote, \
        first_feedback_dt, uncompleted_idea = data_metric_response_time_idea(idea)
        if uncompleted_idea == 1:
            received_feedback = 1
        elif problematic_idea == 1:
            received_feedback = 1
        elif first_react_vote == 1:
            received_feedback = 1
            type_first_feedback = 'vote'
        elif first_react_comment == 1:
            received_feedback = 1
            type_first_feedback = 'comment'
        return idea_by_newcomer, received_feedback, type_first_feedback, \
               first_feedback_dt, response_time_hours
    else:
        return idea_by_newcomer, received_feedback, type_first_feedback, \
               first_feedback_dt, response_time_hours


def problematic_community(community_id):
    TESTING_COMMUNITIES = ['13542', '24523', '2538', '2137', '22174', '25813', '10495',
                           '34206', '8188', '6408', '8538']
    INCOMPLETE_COMMUNITIES = ['20036', '2780', '15287', '23001', '31589', '13493', '18116']
    UNAVAILABLE_COMMUNITIES = ['27159', '27749', '33602', '29324', '31683']
    SPAM_COMMUNITIES = ['27157', '24385']

    if community_id in TESTING_COMMUNITIES: return True
    elif community_id in INCOMPLETE_COMMUNITIES: return True
    elif community_id in UNAVAILABLE_COMMUNITIES: return True
    elif community_id in SPAM_COMMUNITIES: return True
    else: return False


##
# Gather data to later use to
# compute metrics
#
##
def gather_data(communities, authors, data):
    tot_communities = len(data)
    community_counter = 0
    metric_data = {}

    for community_id, ideas in data.iteritems():
        if problematic_community(community_id):
            continue
        community_counter += 1
        print_progress_bar(community_counter, tot_communities, prefix='Progress',
                           suffix='Completed', bar_length=50)
        total_ideas = len(ideas)
        for idx in range(0, total_ideas):
            idea = ideas[idx]
            if idx == 0:
                # initialize community metric vars
                metric_data[community_id] = {}
                metric_data[community_id]['01_ideas'] = total_ideas
                metric_data[community_id]['02_problematic_ideas'] = 0
                metric_data[community_id]['03_attended_ideas'] = 0
                metric_data[community_id]['04_attended_uncompleted_ideas'] = 0
                metric_data[community_id]['05_ignored_ideas'] = 0
                metric_data[community_id]['06_voted_ideas'] = 0
                metric_data[community_id]['07_up_voted_ideas'] = 0
                metric_data[community_id]['08_down_voted_ideas'] = 0
                metric_data[community_id]['09_commented_ideas'] = 0
                metric_data[community_id]['10_attended_only_vote_ideas'] = 0
                metric_data[community_id]['11_attended_only_comment_ideas'] = 0
                metric_data[community_id]['12_attended_vote_comment_ideas'] = 0
                metric_data[community_id]['13_ideas_with_comment_as_first_reaction'] = 0
                metric_data[community_id]['14_ideas_with_vote_as_first_reaction'] = 0
                metric_data[community_id]['15_response_times_ideas'] = []
                metric_data[community_id]['16_comments'] = 0
                metric_data[community_id]['17_ignored_comments'] = 0
                metric_data[community_id]['18_problematic_comments'] = 0
                metric_data[community_id]['19_voted_comments'] = 0
                metric_data[community_id]['20_up_voted_comments'] = 0
                metric_data[community_id]['21_down_voted_comments'] = 0
                metric_data[community_id]['22_replies'] = 0
                metric_data[community_id]['23_voted_replies'] = 0
                metric_data[community_id]['24_up_voted_replies'] = 0
                metric_data[community_id]['25_down_voted_replies'] = 0
                metric_data[community_id]['26_replied_replies'] = 0
                metric_data[community_id]['27_response_times_comments'] = []
                metric_data[community_id]['28_irrelevant_ideas'] = 0
                metric_data[community_id]['29_newcomer_ideas'] = 0
                metric_data[community_id]['30_attended_newcomer_ideas'] = 0
                metric_data[community_id]['31_array_attended_newcomer_ideas'] = []    
            idea_voted, idea_p_voted, idea_n_voted, idea_commented, ignored_idea, attended_idea, \
            idea_only_voted, idea_only_commented, idea_voted_commented = \
            data_metric_number_votes_comments_idea(idea)
            metric_data[community_id]['06_voted_ideas'] += idea_voted
            metric_data[community_id]['07_up_voted_ideas'] += idea_p_voted
            metric_data[community_id]['08_down_voted_ideas'] += idea_n_voted
            metric_data[community_id]['09_commented_ideas'] += idea_commented
            metric_data[community_id]['05_ignored_ideas'] += ignored_idea
            metric_data[community_id]['03_attended_ideas'] += attended_idea
            metric_data[community_id]['10_attended_only_vote_ideas'] += idea_only_voted
            metric_data[community_id]['11_attended_only_comment_ideas'] += idea_only_commented
            metric_data[community_id]['12_attended_vote_comment_ideas'] += idea_voted_commented
            comments, comments_voted, comments_p_voted, comments_n_voted, replies, \
            replies_voted, replies_p_voted, replies_n_voted, replies_replied = \
            data_metric_number_votes_replies_comments(idea)
            metric_data[community_id]['16_comments'] += comments
            metric_data[community_id]['22_replies'] += replies
            metric_data[community_id]['19_voted_comments'] += comments_voted
            metric_data[community_id]['20_up_voted_comments'] += comments_p_voted
            metric_data[community_id]['21_down_voted_comments'] += comments_n_voted
            metric_data[community_id]['23_voted_replies'] += replies_voted
            metric_data[community_id]['24_up_voted_replies'] += replies_p_voted
            metric_data[community_id]['25_down_voted_replies'] += replies_n_voted
            metric_data[community_id]['26_replied_replies'] += replies_replied
            response_time_hour, problematic_idea, first_react_comment, first_react_vote, \
            first_react_dt, uncompleted_idea = data_metric_response_time_idea(idea)
            metric_data[community_id]['02_problematic_ideas'] += problematic_idea
            metric_data[community_id]['04_attended_uncompleted_ideas'] += uncompleted_idea
            metric_data[community_id]['13_ideas_with_comment_as_first_reaction'] += \
                first_react_comment
            metric_data[community_id]['14_ideas_with_vote_as_first_reaction'] += \
                first_react_vote
            if response_time_hour != -999:  # only save response time of completed ideas
                if first_react_vote == 1:
                    type_first_reaction = 'vote'
                else:
                    type_first_reaction = 'comment'
                metric_data[community_id]['15_response_times_ideas'].\
                    append({'idea_id': idea['id'], 'response_time_hour': response_time_hour,
                            'idea_dt': idea['creation_datetime'], 'first_reaction_dt': first_react_dt,
                            'type_first_reaction': type_first_reaction})                                
            ignored_comments, problematic_comments, attended_comments = data_metric_response_time_comments(idea)
            metric_data[community_id]['17_ignored_comments'] += ignored_comments
            metric_data[community_id]['18_problematic_comments'] += problematic_comments
            metric_data[community_id]['27_response_times_comments'] += attended_comments
            metric_data[community_id]['28_irrelevant_ideas'] += data_metric_irrelevant_idea(idea)
            idea_by_newcomer, received_feedback, type_first_feedback, \
            first_feedback_dt, response_time_hours = data_metric_feedback_newcomer_idea(idea, authors)
            metric_data[community_id]['29_newcomer_ideas'] += idea_by_newcomer
            metric_data[community_id]['30_attended_newcomer_ideas'] += received_feedback
            if idea_by_newcomer == 1 and received_feedback == 1 and response_time_hours != -999:
                attended_idea = {'idea_id': idea['id'], 'type_first_feedback': type_first_feedback,
                                 'first_feedback_dt': first_feedback_dt,
                                 'response_time_first_feedback_hours': response_time_hours,
                                 'idea_creation_dt': idea['creation_datetime']}
                metric_data[community_id]['31_array_attended_newcomer_ideas'].append(attended_idea)
        metric_data[community_id]['32_tags_content'] = communities.get(community_id)['tags']

    return metric_data


###
# Load in a dictionary all the ideas, comments, and votes
# grouped by community. The goal is to facilitate the posterior
# calculation of metrics
###
def get_dict(keys, values):
    idea_dict = {}
    if len(keys) == len(values):
        for idx in range(0,len(keys)):
            idea_dict[keys[idx]] = values[idx]
        return idea_dict
    else:
        raise Exception('Dimension miss match')


def build_dataset(fname_ideas, fname_comments, fname_orphan_comments, fname_votes):
    community_ideas, total_dict = [], {}

    with open(fname_ideas, 'rb') as csv_ideas:
        reader_ideas = csv.reader(csv_ideas, delimiter=',')
        list_ideas = list(reader_ideas)
        total_ideas = len(list_ideas)
        header_ideas = list_ideas[0]
        community_id = list_ideas[1][12]
        with open(fname_comments, 'rb') as csv_comments:
            reader_comments = csv.reader(csv_comments, delimiter=',')
            list_comments = list(reader_comments)
            total_comments = len(list_comments)
            comment_pointer = 1  # skip the first line since it contains header info
            orphan_comments = list(open(fname_orphan_comments))
            orphan_comments = [line.rstrip() for line in orphan_comments]  # Take out newline character
            header_comments = list_comments[0]
            hold_replies = []
            with open(fname_votes, 'rb') as csv_votes:
                reader_votes = csv.reader(csv_votes, delimiter=',')
                list_votes = list(reader_votes)
                total_votes = len(list_votes)
                vote_pointer = 2
                header_votes = list_votes[1]
                print('Be patient, we are processing {} ideas, {} comments, and {} votes'.
                      format(total_ideas, total_comments, total_votes))
                for idx_ideas in range(1, total_ideas):
                    print_progress_bar(idx_ideas, total_ideas, prefix='Progress',
                                       suffix='Completed', bar_length=50)
                    line_idea = list_ideas[idx_ideas]
                    try:
                        if line_idea[12] != community_id:
                            # Save ideas when community change
                            total_dict[community_id] = community_ideas
                            community_id = line_idea[12]
                            community_ideas = []
                        # Collect ideas related to the community
                        dict_idea = get_dict(header_ideas, line_idea)
                        idea_id = line_idea[0]
                        idea_comments, comment_ids = [], []
                        # Collect comments related to the idea
                        for idx_comment in range(comment_pointer, total_comments):
                            line_comment = list_comments[idx_comment]
                            if line_comment[0] in orphan_comments:
                                # Ignore orphan comments (comments whose parent (ideas/comment)
                                # are not in the data set)
                                continue
                            else:
                                if line_comment[7] == 'idea':
                                    if line_comment[8] != idea_id:
                                        # Exit the loop when there no more comments to the idea
                                        comment_pointer = idx_comment
                                        break
                                    dict_comment = get_dict(header_comments, line_comment)
                                    idea_comments.append(dict_comment)
                                    comment_ids.append(line_comment[0])
                                    # save held back replies if parent appears
                                    for hold_reply in list(hold_replies):
                                        if hold_reply['parent_id'] == line_comment[0]:
                                            idea_comments.append(hold_reply)
                                            hold_replies.remove(hold_reply)
                                else:
                                    # find whether the parent comment is a comment to this idea
                                    # if yes, save the reply, if not hold back
                                    parent_comment_id = line_comment[8]
                                    # see if parent was already stored in the array
                                    dict_comment = get_dict(header_comments, line_comment)
                                    if parent_comment_id in comment_ids:
                                        idea_comments.append(dict_comment)
                                    else:
                                        hold_replies.append(dict_comment)
                        dict_idea.update({'comments_array': idea_comments})
                        idea_votes = []
                        for idx_vote in range(vote_pointer, total_votes):
                            line_vote = list_votes[idx_vote]
                            if line_vote[2] != idea_id:
                                # Exist the loop when finding votes no related to the idea
                                vote_pointer = idx_vote
                                break
                            dict_vote = get_dict(header_votes, line_vote)
                            idea_votes.append(dict_vote)
                        dict_idea.update({'votes_array': idea_votes})
                        community_ideas.append(dict_idea)
                    except Exception as e:
                        print(e.message)
                        break
                if len(community_ideas) > 0:
                    total_dict[community_id] = community_ideas
                csv_votes.close()
            csv_comments.close()
        csv_ideas.close()

    return total_dict


# Print text-based progress bar
# Author: Greenstick
# Taken from
# http://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
def print_progress_bar(iteration, total, prefix='', suffix='',
                       decimals=2, bar_length=100):
    """
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
    """
    filled_length = int(round(bar_length * iteration / float(total)))
    percents = round(100.00 * (iteration / float(total)), decimals)
    bar = '#' * filled_length + '-' * (bar_length- filled_length)
    sys.stdout.write('%s [%s] %s%s %s\r' % (prefix, bar, percents, '%', suffix)),
    sys.stdout.flush()
    if iteration == total:
        print("\n")


def load_data():
    try:
        with open('data/dataset.json') as json_file:
            j_data = json.load(json_file)
            json_file.close()
            return j_data
    except Exception as e:
        dataset = build_dataset('data/idsc_ideas_no_text_last.csv',
                                'data/idsc_comments_no_text_last.csv',
                                'data/orphaned_comments.txt',
                                'data/idsc_votes_last.csv')
        j_dataset = json.dumps(dataset)
        with open('data/dataset.json', 'w') as json_file:
            json_file.write(j_dataset)
            json_file.close()
        return dataset


def load_communities():
    communities = {}

    with open('data/idsc_communities.csv', 'rb') as csv_communities:
        reader_communities = csv.reader(csv_communities, delimiter=',')
        list_communities = list(reader_communities)
        header = list_communities[1]
        total_communities = len(list_communities)
        for idx in range(2, total_communities):
            community = list_communities[idx]
            communities[community[0]] = get_dict(header, community)

    return communities


def identify_author_reg_datetime(author):
    # identify author registration datetime
    author_len = len(author)
    idx_registration_dt = -1
    num_values = []
    for i in range(0, author_len):
        try:
            datetime.datetime.strptime(author[i].split('.')[0], '%Y-%m-%dT%H:%M:%S')
            idx_registration_dt = i
        except ValueError:
            pass
        try:
            num_values.append(int(author[i]))  # save all numeric values
        except ValueError:
            pass
    return {'idx_reg_dt': idx_registration_dt, 'numeric_values': num_values}


def load_authors():
    authors = {}

    try:
        with open('data/authors.json', 'rb') as json_authors:
            authors = json.load(json_authors)
    except Exception:
        with open('data/idsc_authors_reloaded.csv', 'rb') as csv_author1:
            reader_author1 = csv.reader(csv_author1, delimiter=',')
            list_author1 = list(reader_author1)
            total_author1 = len(list_author1)
            with open('data/idsc_authors_reloaded2.csv', 'rb') as csv_author2:
                reader_author2 = csv.reader(csv_author2, delimiter=',')
                list_author2 = list(reader_author2)
                total_author2 = len(list_author2)
                for idx in range(2, total_author1):
                    author = list_author1[idx]
                    ret = identify_author_reg_datetime(author)
                    if ret['idx_reg_dt'] != -1:
                        # only consider authors whose registration datetime is known
                        authors[author[0]] = {'id': author[0], 'registration_datetime': author[ret['idx_reg_dt']],
                                              # know that community id will be
                                              # always located at the end of the
                                              # array
                                              'community': ret['numeric_values'][-1]}
                for idx in range(2, total_author2):
                    author = list_author2[idx]
                    ret = identify_author_reg_datetime(author)
                    if ret['idx_reg_dt'] != -1:
                        # only consider authors whose registration datetime is known
                        authors[author[0]] = {'id': author[0], 'registration_datetime': author[ret['idx_reg_dt']],
                                              'community': ret['numeric_values'][-1]}
        j_author = json.dumps(authors)
        with open('data/authors.json', 'w') as json_file:
                json_file.write(j_author)

    return authors


def save_data_for_metrics(metric_results):
    j_results = json.dumps(metric_results)
    with open('data/metric_data.json', 'w') as json_file:
        json_file.write(j_results)
        json_file.close()


def collect_data_for_metrics():
    print('Loading file data...')
    data = load_data()
    communities = load_communities()
    authors = load_authors()
    print('Collecting data for metrics, please wait...')
    metrics_data = gather_data(communities, authors, data)
    print('Saving collected data, please wait...')
    save_data_for_metrics(metrics_data)

    return metrics_data


def merge_metric_data(metrics_data):
    m_metric_data = {}

    for metric_id, metric_data in metrics_data.iteritems():
        for community_id, community_data in metric_data.iteritems():
            if metric_id == 'tags_content':
                dict_to_save = {metric_id: community_data}
            else:
                dict_to_save = community_data
            if community_id in m_metric_data.keys():
                m_metric_data[community_id].update(dict_to_save)
            else:
                m_metric_data[community_id] = dict_to_save

    return m_metric_data

##
# Compute the following metrics related to IM communities
#
# 1)  ratio of idea by members
# 2)  ratio of comment by members
# 3)  ratio of vote by members
# 4)  ratio of attended ideas
# 5)  ratio of ideas attended only by votes
# 6)  ratio of ideas attended only by comments
# 7)  ratio of ideas attended by comments and votes
# 8)  ratio of attended ideas whose first feedback was a vote
# 9)  ratio of attended ideas whose first feedback was a comment
# 10) ratio of attended comments
# 11) ratio of replies
# 12) ideas avg. response time, i.e.,
# time between the creation of ideas and their corresponding
# response (comment/vote)
# 13) comments avg. response time, i.e., time between the creation
# of comments and their corresponding reply
# 14) ratio of irrelevant ideas
# 15) ratio of tags used to organize the content by ideas
# 16) ratio of ideas posted by newcomers
# 17) ratio of attended newcomers' ideas
# 18) ratio of voting as first feedback to newcomers' ideas
# 19) ratio of commenting as fist feedback to newcomers' ideas
# 20) newcomer avg. response time, i.e., time between the creation of
# ideas and their corresponding response (comment/vote)
# 21) ratio of ideas created by moderators/administrators
# 22) ratio of comments created by moderators/administrators
# 23) ratio of votes created by moderators/administrators
# 24) ratio of moderators (number of moderators by number of members)
# 25) ratio of ideas as mechanism of intervention
# 26) ratio of votes as mechanism of intervention
# 27) ratio of comments as mechanism of intervention
# 28) ratio of contributors by members
#
##

##
# Computer metrics 1), 2), and 3)
##
def productivity(communities_ds, metric_results):
    for community in communities_ds:
        if community[0] == 'id':
            continue
        num_ideas = int(community[4])
        num_members = int(community[8])
        num_votes = int(community[10])
        num_comments = int(community[13])
        num_contributors = int(community[9])
        prod_ideas = float(num_ideas)/float(num_members)
        prod_votes = float(num_votes)/float(num_members)
        prod_comments = float(num_comments)/float(num_members)
        if num_contributors <= num_members:
            participation = float(num_contributors)/float(num_members)
        else:
            participation = -999
        metric_results[community[0]] = {'ideas_by_members': prod_ideas,
                                        'votes_by_members': prod_votes,
                                        'comments_by_members': prod_comments,
                                        'contributors_by_members': participation}

    return metric_results


##
# Computer metrics 4)-13)
##
def community_responsiveness(community_data):
    community_res_metrics = {}

    # metric: 4) ratio of attended ideas
    r_attended_ideas = float(community_data['03_attended_ideas'])/float(community_data['01_ideas'])
    community_res_metrics['attended_ideas'] = r_attended_ideas

    if int(community_data['03_attended_ideas']) > 0:
        # metric: 5) ratio of ideas attended only by votes
        r_attended_ideas = float(community_data['10_attended_only_vote_ideas'])/\
                           float(community_data['03_attended_ideas'])
        community_res_metrics['ideas_attended_only_by_vote'] = r_attended_ideas
        # metric: 6) ratio of ideas attended only by comments
        r_attended_ideas = float(community_data['11_attended_only_comment_ideas'])/\
                           float(community_data['03_attended_ideas'])
        community_res_metrics['ideas_attended_only_by_comment'] = r_attended_ideas
        # metric: 7) ratio of ideas attended by comments and votes
        r_attended_ideas = float(community_data['12_attended_vote_comment_ideas'])/\
                           float(community_data['03_attended_ideas'])
        community_res_metrics['ideas_attended_by_comment_vote'] = r_attended_ideas
    else:
        community_res_metrics['ideas_attended_only_by_vote'] = 0
        community_res_metrics['ideas_attended_only_by_comment'] = 0
        community_res_metrics['ideas_attended_by_comment_vote'] = 0

    num_unhealthy_ideas = int(community_data['04_attended_uncompleted_ideas']) + \
                          int(community_data['02_problematic_ideas'])
    ratio_unhealthy_ideas = float(num_unhealthy_ideas)/float(community_data['01_ideas'])
    if ratio_unhealthy_ideas <= 0.05:
        # 95% of the ideas must be healthy (completed, i.e., with all their
        # ideas and comments, and non problematic)
        if int(community_data['03_attended_ideas']) > 0:
            # metric: 8) ratio of attended ideas whose first feedback was a vote
            r_attended_ideas = float(community_data['14_ideas_with_vote_as_first_reaction'])/\
                               float(community_data['03_attended_ideas'])
            community_res_metrics['ideas_attended_firstly_by_vote'] = r_attended_ideas
            # metric: 9) ratio of attended ideas whose first feedback was a comment
            r_attended_ideas = float(community_data['13_ideas_with_comment_as_first_reaction'])/\
                               float(community_data['03_attended_ideas'])
            community_res_metrics['ideas_attended_firstly_by_comment'] = r_attended_ideas
        else:
            community_res_metrics['ideas_attended_firstly_by_vote'] = 0
            community_res_metrics['ideas_attended_firstly_by_comment'] = 0
    else:
        community_res_metrics['ideas_attended_firstly_by_vote'] = 0
        community_res_metrics['ideas_attended_firstly_by_comment'] = 0

    num_attended_comments = int(community_data['16_comments']) - \
                            int(community_data['17_ignored_comments'])
    if int(community_data['16_comments']) > 0:
        # metric: 10) ratio of comments attended
        r_attended_comments = float(num_attended_comments)/\
                              float(community_data['16_comments'])
        community_res_metrics['attended_comments'] = r_attended_comments
        # metric: 11) ratio of replies
        r_replies = float(community_data['22_replies'])/float(community_data['16_comments'])
        community_res_metrics['replies_by_comments'] = r_replies
    else:
        community_res_metrics['attended_comments'] = 0
        community_res_metrics['replies_by_comments'] = 0

    # metric 12) avg. response time to ideas
    if ratio_unhealthy_ideas <= 0.05 and int(community_data['03_attended_ideas']) > 0:
        rt_ideas = []
        for idea in community_data['15_response_times_ideas']:
            rt_ideas.append(int(idea['response_time_hour']))
        media_rt = numpy.median(rt_ideas)
        community_res_metrics['ideas_median_response_time_hours'] = media_rt
    else:
        community_res_metrics['ideas_median_response_time_hours'] = 0

    # metric 13) avg. response time to comments
    if int(community_data['16_comments']) > 0 and num_attended_comments > 0:
        ratio_unhealthy_comments = float(community_data['18_problematic_comments'])/\
                                   float(community_data['16_comments'])
        if ratio_unhealthy_comments <= 0.05:
            rt_comments = []
            for comment in community_data['27_response_times_comments']:
                rt_comments.append(int(comment['response_time_hours']))
            media_rt = numpy.median(rt_comments)
            community_res_metrics['comments_median_response_time_hours'] = media_rt
        else:
            community_res_metrics['comments_median_response_time_hours'] = 0
    else:
        community_res_metrics['comments_median_response_time_hours'] = 0

    return community_res_metrics


##
# Computer metrics 14), 15)
##
def content_quality(community_data):
    community_q_metrics = {}

    # metric: 14) ratio of irrelevant ideas
    r_irrelevant_ideas = float(community_data['28_irrelevant_ideas'])/float(community_data['01_ideas'])
    community_q_metrics['irrelevant_ideas'] = r_irrelevant_ideas
    # metric: 15) ratio of tags by ideas
    r_tags_ideas = float(community_data['32_tags_content'])/float(community_data['01_ideas'])
    community_q_metrics['tags_by_ideas'] = r_tags_ideas

    return community_q_metrics


##
# Compute metrics 16)-20)
##
def newcomers_treatment(community_data):
    community_nc_metrics = {}

    # metric: 16) ratio of ideas posted by newcomers
    community_nc_metrics['newcomer_ideas'] = float(community_data['29_newcomer_ideas'])/\
                                             float(community_data['01_ideas'])

    # metric: 17) ratio of attended newcomers' ideas
    if int(community_data['29_newcomer_ideas']) > 0:
        community_nc_metrics['attended_newcomer_ideas'] = float(community_data['30_attended_newcomer_ideas'])/\
                                                          float(community_data['29_newcomer_ideas'])
    else:
        community_nc_metrics['attended_newcomer_ideas'] = 0

    # metric: 18)-20) ratio of voting as first feedback to newcomers' ideas
    num_unhealthy_ideas = int(community_data['04_attended_uncompleted_ideas']) + \
                          int(community_data['02_problematic_ideas'])
    ratio_unhealthy_ideas = float(num_unhealthy_ideas)/float(community_data['01_ideas'])
    if ratio_unhealthy_ideas <= 0.05:
        num_first_feedback_comments, num_first_feedback_votes = 0, 0
        feedback_rt = []
        for feedback in community_data['31_array_attended_newcomer_ideas']:
            if feedback['type_first_feedback'] == 'vote':
                num_first_feedback_votes += 1
            else:
                num_first_feedback_comments += 1
            feedback_rt.append(int(feedback['response_time_first_feedback_hours']))
        if int(community_nc_metrics['attended_newcomer_ideas']) > 0:
            # metric: 18) ratio of voting as first feedback to newcomers' ideas
            community_nc_metrics['vote_first_feedback_newcomer_ideas'] = \
                float(num_first_feedback_votes)/float(community_data['30_attended_newcomer_ideas'])
            # metric: 19) ratio of commenting as fist feedback to newcomers' ideas
            community_nc_metrics['comment_first_feedback_newcomer_ideas'] = \
            float(num_first_feedback_comments)/float(community_data['30_attended_newcomer_ideas'])
            # metric: 20) avg. response time to newcomer ideas
            media_rt = numpy.median(feedback_rt)
            community_nc_metrics['newcomer_ideas_median_response_time_hours'] = media_rt
        else:
            community_nc_metrics['vote_first_feedback_newcomer_ideas'] = 0
            community_nc_metrics['comment_first_feedback_newcomer_ideas'] = 0
            community_nc_metrics['newcomer_ideas_median_response_time_hours'] = 0
    else:
        community_nc_metrics['vote_first_feedback_newcomer_ideas'] = 0
        community_nc_metrics['comment_first_feedback_newcomer_ideas'] = 0
        community_nc_metrics['newcomer_ideas_median_response_time_hours'] = 0

    return community_nc_metrics


##
# Compute metrics 21)-27)
##
def moderator_interventions(communities_ds, metric_results):
    for community in communities_ds:
        if community[0] == 'id':
            continue
        num_ideas = int(community[4])
        num_members = int(community[8])
        num_votes = int(community[10])
        num_comments = int(community[13])
        inter_ideas = int(community[21])
        inter_votes = int(community[22])
        inter_comments = int(community[23])
        total_inter = int(community[24])
        moderators = int(community[18])
        if num_ideas > 0:
            r_inter_ideas = float(inter_ideas)/float(num_ideas)
        else:
            r_inter_ideas = 0
        if num_votes > 0:
            r_inter_votes = float(inter_votes)/float(num_votes)
        else:
            r_inter_votes = 0
        if num_comments > 0:
            r_inter_comments = float(inter_comments)/float(num_comments)
        else:
            r_inter_comments = 0
        r_moderators = float(moderators)/float(num_members)
        if total_inter > 0:
            r_inter_type_ideas = float(inter_ideas)/float(total_inter)
            r_inter_type_votes = float(inter_votes)/float(total_inter)
            r_inter_type_comments = float(inter_comments)/float(total_inter)
        else:
            r_inter_type_ideas, r_inter_type_votes, r_inter_type_comments = 0, 0, 0
        metric_results[community[0]].update({'ratio_moderators': r_moderators,
                                             'ratio_ideas_by_moderators': r_inter_ideas,
                                             'ratio_votes_by_moderators': r_inter_votes,
                                             'ratio_comments_by_moderators': r_inter_comments,
                                             'ratio_type_inter_ideas': r_inter_type_ideas,
                                             'ratio_type_inter_votes': r_inter_type_votes,
                                             'ratio_type_inter_comments': r_inter_type_comments})

    return metric_results


def compute_metrics():
    # load data collected previously to compute metrics
    try:
        with open('data/metric_data.json', 'rb') as json_m_data:
            m_data = json.load(json_m_data)
    except IOError as e:
        m_data = collect_data_for_metrics()
    except Exception as e:
        print e
        return
    # load data about community interventions
    with open('data/communities_dataset.csv', 'rb') as csv_communities:
        overall_communities = csv.reader(csv_communities, delimiter=',')
        communities = list(overall_communities)
        community_metrics = {}
        # compute productivity metrics
        community_metrics = productivity(communities, community_metrics)
        # compute intervention metrics
        community_metrics = moderator_interventions(communities, community_metrics)
        for community_id, community_data in m_data.iteritems():
            if community_id == '33443':
                pass
            # compute responsiveness metrics
            community_metrics[community_id].update(community_responsiveness(community_data))
            # compute content quality
            community_metrics[community_id].update(content_quality(community_data))
            # compute newcomer treatment
            community_metrics[community_id].update(newcomers_treatment(community_data))

    return community_metrics


def save_metric_results(community_metrics):
    with open('data/community_metrics.csv', 'w') as csv_output:
        output = csv.writer(csv_output, delimiter=',')
        header = ['community_id', 'ideas_by_members', 'comments_by_members', 'votes_by_members',
                  'attended_ideas_by_ideas', 'ideas_attended_by_votes_by_ideas',
                  'ideas_attended_by_comments_by_ideas', 'ideas_attended_by_votes_and_comments_by_ideas',
                  'ideas_attended_firstly_by_vote_by_ideas', 'ideas_attended_firstly_by_comment_by_ideas',
                  'median_response_time_ideas_hs', 'attended_comments_by_comments',
                  'replies_by_comments', 'median_response_time_comments_hs', 'irrelevant_ideas_by_ideas',
                  'tags_by_ideas', 'newcomer_ideas_by_ideas', 'attended_newcomer_ideas_by_newcomer_ideas',
                  'newcomer_ideas_attended_firstly_by_vote_by_newcomer_ideas',
                  'newcomer_ideas_attended_firstly_by_comment_by_newcomer_ideas',
                  'median_response_time_newcomer_ideas_hs', 'moderator_ideas_by_ideas',
                  'moderator_comments_by_comments', 'moderator_votes_by_votes', 'moderators_by_members',
                  'moderator_ideas_by_interventions', 'moderator_comments_by_interventions',
                  'moderator_votes_by_interventions', 'contributors_by_members']
        output.writerow(header)
        for community_id, community_data in community_metrics.iteritems():
            row = [community_id, community_data['ideas_by_members'], community_data['comments_by_members'],
                   community_data['votes_by_members'], community_data['attended_ideas'],
                   community_data['ideas_attended_only_by_vote'], community_data['ideas_attended_only_by_comment'],
                   community_data['ideas_attended_by_comment_vote'],
                   community_data['ideas_attended_firstly_by_vote'],
                   community_data['ideas_attended_firstly_by_comment'],
                   community_data['ideas_median_response_time_hours'], community_data['attended_comments'],
                   community_data['replies_by_comments'], community_data['comments_median_response_time_hours'],
                   community_data['irrelevant_ideas'], community_data['tags_by_ideas'],
                   community_data['newcomer_ideas'], community_data['attended_newcomer_ideas'],
                   community_data['vote_first_feedback_newcomer_ideas'],
                   community_data['comment_first_feedback_newcomer_ideas'],
                   community_data['newcomer_ideas_median_response_time_hours'],
                   community_data['ratio_ideas_by_moderators'],
                   community_data['ratio_comments_by_moderators'], community_data['ratio_votes_by_moderators'],
                   community_data['ratio_moderators'], community_data['ratio_type_inter_ideas'],
                   community_data['ratio_type_inter_comments'], community_data['ratio_type_inter_votes'],
                   community_data['contributors_by_members']]
            output.writerow(row)


if __name__ == '__main__':
    print('Computing metrics, please wait...')
    metric_results = compute_metrics()
    print('Saving metric results, please wait...')
    save_metric_results(metric_results)