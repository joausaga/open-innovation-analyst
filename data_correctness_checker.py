__author__ = 'jorgesaldivar'


import csv


def exists_idea_in_community(ideas_vec, idea_id, community_id):
    total_ideas = len(ideas_vec)

    for idx in range(0, total_ideas):
        line_idea = ideas_vec[idx]
        if line_idea[12] == community_id:
            if line_idea[0] == idea_id:
                return True
        else:
            return False

    return False


def remove_ideas(ideas_vec, community_id):
    total_ideas = len(ideas_vec)
    idx_to_remove = 0

    for idx in range(0, total_ideas):
        line_idea = ideas_vec[idx]
        if line_idea[12] == community_id:
            idx_to_remove += 1
        else:
            break

    ideas_vec = ideas_vec[idx_to_remove:]
    return ideas_vec


if __name__ == '__main__':
    print('Checking data correctness...')

    errors = []
    num_errors = 0
    total_errors = 0
    community_id = None
    error_ids = []
    total_comments = 0
    orphaned_replies = []

    with open('data/idsc_ideas_no_text_last.csv') as csv_ideas:
        reader_ideas = csv.reader(csv_ideas, delimiter=',')
        list_ideas = list(reader_ideas)[1:]
        with open('data/idsc_comments_no_text_last.csv') as csv_comments:
            reader_comments = csv.reader(csv_comments, delimiter=',')
            for comment in reader_comments:
                if comment[0] == 'Observation Date':
                    continue
                if comment[0] == 'id':
                    continue
                total_comments += 1
                if community_id is None:
                    community_id = comment[9]
                if community_id != comment[9]:
                    num_orphaned_replies = len(orphaned_replies)
                    if num_orphaned_replies > 0:
                        num_errors += len(orphaned_replies)
                        total_errors += len(orphaned_replies)
                        for orphaned_reply in orphaned_replies:
                            error_ids.append(orphaned_reply[0])
                    if num_errors > 0 and community_id is not None:
                        errors.append({'community': community_id,
                                       'errors': num_errors,
                                       'ids': error_ids})
                    # Delete from list ideas belonging to previous community
                    # Implemented this as a loop to take of communities
                    # without comments
                    while list_ideas[0][12] != comment[9]:
                        list_ideas = remove_ideas(list_ideas, community_id)
                        community_id = list_ideas[0][12]
                    community_id = comment[9]
                    num_errors = 0
                    error_ids = []
                    orphaned_replies = []
                parent_type = comment[7]
                if parent_type == 'idea':
                    # search parent
                    for reply in list(orphaned_replies):
                        if reply[8] == comment[0]:
                            orphaned_replies.pop(orphaned_replies.index(reply))
                    if not exists_idea_in_community(list_ideas, comment[8], comment[9]):
                        total_errors += 1
                        num_errors += 1
                        error_ids.append(comment[0])
                else:
                    # assume that reply is orphaned
                    orphaned_replies.append(comment)
            csv_comments.close()
        csv_ideas.close()

    # Print out a report and save into a file the id of the
    # "orphan" comments, comments whose idea parents exist
    # but were missed during the creation of the data set
    f_orphan = open('data/orphaned_comments.txt', 'w')
    f_output = open('data/output_checker.txt', 'w')
    f_output.write('Out of {} comments, {} ({}) have problems\n\n\n'.
                    format(total_comments, total_errors,
                           float(total_errors)/float(total_comments)))
    for error in errors:
        output_line = 'Community {} --------------------------------\n'.format(error['community'])
        output_line += 'It has {} comments placed to ideas that could\'nt be found within the community\n'.\
                        format(error['errors'])
        output_line += 'Comment ids: {}\n\n'.format(error['ids'])
        f_output.write(output_line)
        for error_id in error['ids']:
            f_orphan.write('{}\n'.format(error_id))
    f_output.close()
    f_orphan.close()
