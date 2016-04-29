__author__ = 'jorgesaldivar'

from dateutil import parser

import csv
import datetime
import json
import sys


###
# Metric: Response time of comments
#
# Compute the time that passes between
# the creation of a comment and its
# first reply
#
###
def metric_response_time_comments(idea):
    ignored_comments, problematic_comments = 0, 0
    num_comments, num_replies = 0, 0
    vec_comments, attended_comments = {}, []

    for comment in idea['comments_array']:
        if comment['parent_type'] == 'idea':
            try:
                vec_comments[comment['id']]['creation_dt'] = parser.parse(comment['creation_datetime'])
            except KeyError:
                vec_comments[comment['id']] = {'creation_dt': parser.parse(comment['creation_datetime']),
                                               'replies': []}
            num_comments += 1
        else:
            # found a reply, save
            try:
                vec_comments[comment['parent_id']]['replies'].append(comment)
            except KeyError:
                vec_comments[comment['parent_id']] = {'creation_dt': '', 'replies': [comment]}
            num_replies += 1

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
        else:
            ignored_comments += 1
            response_time_hours = -999
            first_reaction_dt = ''
        attended_comments.append({'comment_id': comment_id,
                                  'comment_dt': comment['creation_dt'].strftime('%Y-%m-%d %H:%M:%S%z'),
                                  'first_reaction_dt': first_reaction_dt,
                                  'response_time_hours': response_time_hours})

    return num_comments, num_replies, ignored_comments, \
           problematic_comments, attended_comments


####
# Metric: Response time of ideas
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


def metric_response_time_idea(idea):
    ignored_idea, problematic_idea = 0, 0
    first_reaction_comment, first_reaction_vote = 0, 0
    first_reaction_dt = ''

    idea_creation_time = parser.parse(idea['creation_datetime'])
    num_comments = len(idea['comments_array'])
    num_votes = len(idea['votes_array'])
    comments_sorted, votes_sorted = None, None

    if num_comments == 0 and num_votes == 0:
        ignored_idea = 1
        response_time_hours = -999
    else:
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

    return response_time_hours, ignored_idea, problematic_idea, first_reaction_comment, \
           first_reaction_vote, first_reaction_dt


####
# Metric: Comments voted and replied
#
# Compute the number of votes (positive and negatives)
# and replies that the comments received
#
####
def metric_number_votes_replies_comments(idea):
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
# Metric: Ideas voted and commented
#
# Compute the number of votes (positive and negatives)
# and comments that ideas received
#
####
def metric_number_votes_comments_idea(idea):
    idea_commented, idea_voted, idea_p_voted, idea_n_voted = 0, 0, 0, 0

    if idea['up_votes'] != '0' or idea['down_votes'] != '0':
        idea_voted = 1
        if idea['up_votes'] != '0':
            idea_p_voted = 1
        else:
            idea_n_voted = 1
    if idea['comments'] != '0':
        idea_commented += 1

    return idea_voted, idea_p_voted, idea_n_voted, idea_commented


###
# Metric: Ideas off-topic
#
# Check whether idea was classified as off-topic
#
####
def metric_offtopic_idea(idea):
    if idea['status'] == 'offtopic':
        return 1
    else:
        return 0


###
# Metric: Feedback on Newcomer Ideas
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


def metric_feedback_newcomer_idea(idea, authors):
    idea_by_newcomer, received_feedback = 0, 0
    type_first_feedback, first_feedback_dt = '', ''
    comments_sorted, votes_sorted = None, None
    response_time_hours = -999

    idea_creator = created_by_newcomer(idea, authors)
    if idea_creator['isnewcomer']:
        idea_by_newcomer = 1
        num_comments = len(idea['comments_array'])
        num_votes = len(idea['votes_array'])
        idea_creation_time = parser.parse(idea['creation_datetime'])
        if num_comments == 0 and num_votes == 0:
            return idea_by_newcomer, received_feedback, type_first_feedback, \
                   first_feedback_dt, response_time_hours
        else:
            received_feedback = 1
            if num_comments > 0:
                comments_sorted = sort_elements_chronologically(idea['comments_array'])
            if num_votes > 0:
                votes_sorted = sort_elements_chronologically(idea['votes_array'])
            if comments_sorted:
                if votes_sorted:
                    if comments_sorted[0] > votes_sorted[0]:  # '>' means which is newer
                        first_feedback = votes_sorted[0]
                        type_first_feedback = 'vote'
                    else:
                        first_feedback = comments_sorted[0]
                        type_first_feedback = 'comment'
                else:
                    first_feedback = comments_sorted[0]
                    type_first_feedback = 'comment'
            else:
                first_feedback = votes_sorted[0]
                type_first_feedback = 'vote'
            response_time = first_feedback - idea_creation_time
            if response_time.total_seconds() > 0:
                response_time_hours = response_time.total_seconds() / 3600
            first_feedback_dt = first_feedback.strftime('%Y-%m-%d %H:%M:%S%z')
            return idea_by_newcomer, received_feedback, type_first_feedback, \
                   first_feedback_dt, response_time_hours
    else:
        return idea_by_newcomer, received_feedback, type_first_feedback, \
               first_feedback_dt, response_time_hours


# Structure metrics parameter
# {metric1_id:
#   {community1_id:
#       {var1:value_var1,
#       ...},
#   community2_id:
#       {var1:value_var1, ...}
#   },
#   metric2_id: {...},
#   metric3_id: {...},
#   ...
# }
# Example:
# metrics = {'votes_comments_ideas':
#               {'8825':
#                   {'voted_ideas':0,
#                    'up_voted_ideas: 0,
#                    'down_voted_ideas: 0,
#                    'commented_ideas: 0
#                   },
#                 '2203':
#                   {'voted_ideas': 0,...},
#                 ...},
#            'votes_replies_comments':
#               {'8825':{...},'2203':{...}},
#             ...
#            }
def compute_metrics(communities, authors, data, metrics):
    tot_communities = len(data)
    community_counter = 0

    for community_id, ideas in data.iteritems():
        community_counter += 1
        print_progress_bar(community_counter, tot_communities, prefix='Progress',
                           suffix='Completed', bar_length=50)
        total_ideas = len(ideas)
        for idx in range(0, total_ideas):
            idea = ideas[idx]
            if 'votes_comments_ideas' in metrics.keys():  # it means that the metric has to be computed
                if idx == 0:
                    # initialize metric vars
                    metrics['votes_comments_ideas'][community_id] = {}
                    metrics['votes_comments_ideas'][community_id]['ideas'] = total_ideas
                    metrics['votes_comments_ideas'][community_id]['voted_ideas'] = 0
                    metrics['votes_comments_ideas'][community_id]['up_voted_ideas'] = 0
                    metrics['votes_comments_ideas'][community_id]['down_voted_ideas'] = 0
                    metrics['votes_comments_ideas'][community_id]['commented_ideas'] = 0
                idea_voted, idea_p_voted, idea_n_voted, idea_commented = metric_number_votes_comments_idea(idea)
                metrics['votes_comments_ideas'][community_id]['voted_ideas'] += idea_voted
                metrics['votes_comments_ideas'][community_id]['up_voted_ideas'] += idea_p_voted
                metrics['votes_comments_ideas'][community_id]['down_voted_ideas'] += idea_n_voted
                metrics['votes_comments_ideas'][community_id]['commented_ideas'] += idea_commented
            if 'votes_replies_comments' in metrics.keys():
                if idx == 0:
                    # initialize metric vars
                    metrics['votes_replies_comments'][community_id] = {}
                    metrics['votes_replies_comments'][community_id]['replies'] = 0
                    metrics['votes_replies_comments'][community_id]['voted_comments'] = 0
                    metrics['votes_replies_comments'][community_id]['up_voted_comments'] = 0
                    metrics['votes_replies_comments'][community_id]['down_voted_comments'] = 0
                    metrics['votes_replies_comments'][community_id]['voted_replies'] = 0
                    metrics['votes_replies_comments'][community_id]['up_voted_replies'] = 0
                    metrics['votes_replies_comments'][community_id]['down_voted_replies'] = 0
                    metrics['votes_replies_comments'][community_id]['replied_replies'] = 0
                    metrics['votes_replies_comments'][community_id]['comments'] = 0
                comments, comments_voted, comments_p_voted, comments_n_voted, replies, \
                replies_voted, replies_p_voted, replies_n_voted, replies_replied = \
                metric_number_votes_replies_comments(idea)
                metrics['votes_replies_comments'][community_id]['comments'] += comments
                metrics['votes_replies_comments'][community_id]['replies'] += replies
                metrics['votes_replies_comments'][community_id]['voted_comments'] += comments_voted
                metrics['votes_replies_comments'][community_id]['up_voted_comments'] += comments_p_voted
                metrics['votes_replies_comments'][community_id]['down_voted_comments'] += comments_n_voted
                metrics['votes_replies_comments'][community_id]['voted_replies'] += replies_voted
                metrics['votes_replies_comments'][community_id]['up_voted_replies'] += replies_p_voted
                metrics['votes_replies_comments'][community_id]['down_voted_replies'] += replies_n_voted
                metrics['votes_replies_comments'][community_id]['replied_replies'] += replies_replied
            if 'response_time_ideas' in metrics.keys():
                if idx == 0:
                    metrics['response_time_ideas'][community_id] = {}
                    metrics['response_time_ideas'][community_id]['ideas'] = total_ideas
                    metrics['response_time_ideas'][community_id]['ignored_ideas'] = 0
                    metrics['response_time_ideas'][community_id]['problematic_ideas'] = 0
                    metrics['response_time_ideas'][community_id]['ideas_with_comment_as_first_reaction'] = 0
                    metrics['response_time_ideas'][community_id]['ideas_with_vote_as_first_reaction'] = 0
                    metrics['response_time_ideas'][community_id]['response_times'] = []
                response_time_hour, ignored_idea, problematic_idea, first_react_comment, first_react_vote, \
                first_react_dt = metric_response_time_idea(idea)
                metrics['response_time_ideas'][community_id]['ignored_ideas'] += ignored_idea
                metrics['response_time_ideas'][community_id]['problematic_ideas'] += problematic_idea
                metrics['response_time_ideas'][community_id]['ideas_with_comment_as_first_reaction'] += \
                    first_react_comment
                metrics['response_time_ideas'][community_id]['ideas_with_vote_as_first_reaction'] += \
                    first_react_vote
                if first_react_vote == 1:
                    type_first_reaction = 'vote'
                else:
                    type_first_reaction = 'comment'
                metrics['response_time_ideas'][community_id]['response_times'].\
                    append({'idea_id': idea['id'], 'response_time_hour:': response_time_hour,
                            'idea_dt': idea['creation_datetime'], 'first_reaction_dt': first_react_dt,
                            'type_first_reaction': type_first_reaction})
            if 'response_time_comments' in metrics.keys():
                if idx == 0:
                    metrics['response_time_comments'][community_id] = {}
                    metrics['response_time_comments'][community_id]['comments'] = 0
                    metrics['response_time_comments'][community_id]['replies'] = 0
                    metrics['response_time_comments'][community_id]['ignored_comments'] = 0
                    metrics['response_time_comments'][community_id]['problematic_comments'] = 0
                    metrics['response_time_comments'][community_id]['response_times'] = []
                comments, replies, ignored_comments, problematic_comments, attended_comments = \
                    metric_response_time_comments(idea)
                metrics['response_time_comments'][community_id]['comments'] += comments
                metrics['response_time_comments'][community_id]['replies'] += replies
                metrics['response_time_comments'][community_id]['ignored_comments'] += ignored_comments
                metrics['response_time_comments'][community_id]['problematic_comments'] += problematic_comments
                metrics['response_time_comments'][community_id]['response_times'] += attended_comments
            if 'offtopic_content' in metrics.keys():
                if idx == 0:
                    # initialize metric vars
                    metrics['offtopic_content'][community_id] = {}
                    metrics['offtopic_content'][community_id]['ideas'] = total_ideas
                    metrics['offtopic_content'][community_id]['offtopic_ideas'] = 0
                metrics['offtopic_content'][community_id]['offtopic_ideas'] += metric_offtopic_idea(idea)
            if 'treatment_newcomers' in metrics.keys():
                if idx == 0:
                    metrics['treatment_newcomers'][community_id] = {}
                    metrics['treatment_newcomers'][community_id]['ideas'] = total_ideas
                    metrics['treatment_newcomers'][community_id]['newcomer_ideas'] = 0
                    metrics['treatment_newcomers'][community_id]['attended_newcomer_ideas'] = 0
                    metrics['treatment_newcomers'][community_id]['attended_ideas'] = []
                idea_by_newcomer, received_feedback, type_first_feedback, \
                first_feedback_dt, response_time_hours = metric_feedback_newcomer_idea(idea, authors)
                metrics['treatment_newcomers'][community_id]['newcomer_ideas'] += idea_by_newcomer
                metrics['treatment_newcomers'][community_id]['attended_newcomer_ideas'] += received_feedback
                if idea_by_newcomer == 1 and received_feedback == 1 and response_time_hours != -999:
                    attended_idea = {'idea_id': idea['id'], 'type_first_feedback': type_first_feedback,
                                     'first_feedback_dt': first_feedback_dt,
                                     'response_time_first_feedback_hours': response_time_hours,
                                     'idea_creation_dt': idea['creation_datetime']}
                    metrics['treatment_newcomers'][community_id]['attended_ideas'].append(attended_idea)
        if 'tags_content' in metrics.keys():
            metrics['tags_content'][community_id] = communities.get(community_id)['tags']

    return metrics

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
            with open(fname_votes, 'rb') as csv_votes:
                reader_votes = csv.reader(csv_votes, delimiter=',')
                list_votes = list(reader_votes)
                total_votes = len(list_votes)
                vote_pointer = 2
                header_votes = list_votes[1]
                print('Be patient, we are processing {} ideas, {} comments, and {} votes'.
                      format(total_ideas, total_comments, total_votes))
                for idx_ideas in range(1, total_ideas):
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
                        idea_comments, hold_replies = [], []
                        comment_ids, parent_ids = [], []
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
                                    if line_comment[0] in parent_ids:
                                        idea_comments += hold_replies
                                        hold_replies = []
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
                                        parent_ids.append(parent_comment_id)
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


def save_results(metric_results):
    j_results = json.dumps(metric_results)
    with open('data/metric_results.json', 'w') as json_file:
        json_file.write(j_results)
        json_file.close()


if __name__ == '__main__':
    print('Loading data...')
    data = load_data()
    communities = load_communities()
    authors = load_authors()
    print('Processing data for metrics, please wait...')
    metrics = {'votes_comments_ideas': {},
               'votes_replies_comments': {},
               'response_time_ideas': {},
               'response_time_comments': {},
               'offtopic_content': {},
               'tags_content': {},
               'treatment_newcomers': {}}
    metrics = compute_metrics(communities, authors, data, metrics)
    print('Saving processed data, please wait...')
    save_results(metrics)
    print('Done!')