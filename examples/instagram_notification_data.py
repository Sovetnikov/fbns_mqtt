import json
from urllib.parse import urlsplit, parse_qs

# The following events are emitted.

#   Posts:
#     - post - "USERNAME just shared a post."
#       media?id=1111111111111111111_1111111111
#     - first_post - "See NAME's first Instagram post."
#       user?username=USERNAME
#     - resurrected_user_post - "USERNAME posted for the first time in a while. Be the first to add a comment."
#       media?id=1111111111111111111_1111111111
#     - recent_follow_post - "USERNAME just shared a post."
#       media?id=1111111111111111111_1111111111
#     - fb_first_post - "Your Facebook friend NAME just shared their first Instagram post"
#       user?username=USERNAME
#     - first_bestie_post - "USERNAME just shared a post with their close friends list."
#       media?id=1111111111111111111_1111111111
#     - follower_activity_with_location - "USERNAME tagged LOCATION in a post."
#       media?id=1111111111111111111 <- Yep, no author ID here.

#   Stories:
#     - first_reel_post - "See USERNAME's first story on Instagram."
#       user?username=USERNAME&launch_reel=1
#     - resurrected_reel_post - "USERNAME added to their story for the first time in a while."
#       user?username=USERNAME&launch_reel=1
#     - first_bestie_post - "USERNAME just shared a post with their close friends list."
#       user?username=USERNAME&launch_reel=1
#     - story_poll_vote - "USERNAME voted YES to "POLL". Currently: 2 YES, 1 NO"
#       user?username=USERNAME&launch_reel=1&media_id=1111111111111111111_1111111111&include_viewers=1
#     - story_poll_close - "Your poll, "POLL" ends in an hour. Results so far: 2 YES, 1 NO"
#       user?username=USERNAME&launch_reel=1&media_id=1111111111111111111_1111111111&include_viewers=1
#     - story_producer_expire_media - "Your story has NUMBER views. Find out who's seen it before it disappears."
#       user?username=USERNAME&launch_reel=1
#     - story_poll_result_share - "Your poll is almost over, and YES is winning. See and share the results."
#       user?username=USERNAME&launch_reel=1&media_id=1111111111111111111_1111111111&include_viewers=1
#     - story_daily_digest - "USERNAME1, USERNAME2 and USERNAME3 recently added to their stories."
#       mainfeed?launch_reel_user_ids=1111111111,2222222222,3333333333,4444444444

#   Followers and contacts:
#     - new_follower - "NAME (USERNAME) started following you."
#       user?username=USERNAME
#     - private_user_follow_request - "NAME (@USERNAME) has requested to follow you."
#       user?username=USERNAME
#     - follow_request_approved - "USERNAME accepted your follow request. Now you can see their photos and videos."
#       user?username=USERNAME
#     - contactjoined - "Your Facebook friend NAME is on Instagram as USERNAME."
#       user?username=USERNAME
#     - contact_joined_email - "NAME, one of your contacts, is on Instagram as @USERNAME. Would you like to follow them?"
#       user?username=USERNAME
#     - fb_friend_connected - "Your Facebook friend NAME is on Instagram as USERNAME."
#       user?username=USERNAME
#     - follower_follow - "USERNAME1 and USERNAME2 followed NAME on Instagram. See their posts."
#       user?username=USERNAME
#     - follower_activity_reminders - "USERNAME1, USERNAME2 and others shared NUMBER photos."
#       mainfeed

#   Comments:
#     - comment - "USERNAME commented: "TEXT""
#       media?id=1111111111111111111_1111111111&forced_preview_comment_id=11111111111111111
#       comments_v2?media_id=1111111111111111111_1111111111&target_comment_id=11111111111111111
#     - mentioned_comment - "USERNAME mentioned you in a comment: TEXT..."
#       media?id=1111111111111111111_1111111111
#       comments_v2?media_id=1111111111111111111_1111111111
#     - comment_on_tag - "USERNAME commented on a post you're tagged in."
#       media?id=1111111111111111111 <- Yep, no author ID here.
#     - comment_subscribed - "USERNAME also commented on USERNAME's post: "TEXT""
#       comments_v2?media_id=1111111111111111111_1111111111&target_comment_id=11111111111111111
#     - comment_subscribed_on_like - "USERNAME commented on a post you liked: TEXT"
#       comments_v2?media_id=1111111111111111111_1111111111&target_comment_id=11111111111111111
#     - reply_to_comment_with_threading - "USERNAME replied to your comment on your post: "TEXT""
#       comments_v2?media_id=1111111111111111111_1111111111&target_comment_id=11111111111111111

#   Likes:
#     - like - "USERNAME liked your post."
#       media?id=1111111111111111111_1111111111
#     - like_on_tag - "USERNAME liked a post you're tagged in."
#       media?id=1111111111111111111_1111111111
#     - comment_like - "USERNAME liked your comment: "TEXT...""
#       media?id=1111111111111111111_1111111111&forced_preview_comment_id=11111111111111111

#   Direct:
#     - direct_v2_message - "USERNAME sent you a message."
#       direct_v2?id=11111111111111111111111111111111111111&x=11111111111111111111111111111111111
#     - direct_v2_message - "USERNAME wants to send you a message."
#       direct_v2?id=11111111111111111111111111111111111111&t=p
#     - direct_v2_message - "USERNAME sent you a photo."
#       direct_v2?id=11111111111111111111111111111111111111&x=11111111111111111111111111111111111&t=ds

#   Live:
#     - live_broadcast - "USERNAME started a live video. Watch it before it ends!"
#       broadcast?id=11111111111111111&reel_id=1111111111&published_time=1234567890
#     - live_with_broadcast - "USERNAME1 is going live now with USERNAME2."
#       broadcast?id=11111111111111111&reel_id=1111111111&published_time=1234567890
#     - live_broadcast_revoke
#       broadcast?id=11111111111111111&reel_id=1111111111&published_time=1234567890

#   Business:
#     - aymt - "Your promotion was approved." or "Your promotion has ended." or internationalized message.
#       media?id=1111111111111111111 <- Yep, no author ID here.
#     - ad_preview - "Your ad is ready to preview"
#       media?id=1111111111111111111_1111111111
#     - branded_content_tagged - "USERNAME tagged you as a business partner on a post."
#       media?id=1111111111111111111_1111111111
#     - branded_content_untagged - "USERNAME removed you as a business partner on a post."
#       media?id=1111111111111111111_1111111111
#     - business_profile - "Add a website so customers can learn about your business."
#       editprofile?user_id=1111111111

#   Unsorted:
#     - usertag - "USERNAME tagged you in a post"
#       media?id=1111111111111111111_1111111111
#     - video_view_count - "People viewed your video more than NUMBER times."
#       media?id=1111111111111111111_1111111111
#     - copyright_video - "Your video may have copyrighted content that belongs to someone else."
#       news
#     - report_updated - "Your support request from DATE was just updated."
#       news
#     - promote_account - "Check out today's photo from TEXT."
#       user?username=USERNAME
#     - unseen_notification_reminders
#       news

#   System:
#     - silent_push - Some kind of service push that does nothing. Nothing important, I hope.
#     - incoming - The event that catches all pushes. Useful for debugging and logging.
#     - warning - An exception of severity "warning" occured.
#     - error - An exception of severity "error" occurred. It's not guaranteed that the Push client will continue to work.


def _spop(d, k):
    if k in d:
        return d.pop(k)
    return None

class BadgeCount(object):
    def __init__(self, data):
        if isinstance(data,str):
            data = json.loads(data)
        self.direct = _spop(data, 'di')
        self.ds = _spop(data, 'ds')
        self.td = _spop(data, 'dt')
        self.activities = _spop(data, 'ac')
        if data:
            raise Exception('BadgeCount unexpected data: {data}'.format(**locals()))


class InstagramNotification(object):
    def __str__(self):
        return str(self.__dict__)

    def __init__(self, data):
        if isinstance(data, str):
            data = json.loads(data)

        # For sentry debug
        original_data = dict(data)

        self.title = _spop(data, 't')
        self.message = _spop(data, 'm')
        self.tickerText = _spop(data, 'tt')

        self.igAction = _spop(data, 'ig')
        self.actionPath = None
        self.actionParams = None

        if self.igAction:
            scheme, netloc, path, query_string, fragment = urlsplit(self.igAction)
            query_params = parse_qs(query_string)
            query_params = dict((k, v if len(v) > 1 else v[0]) for k, v in query_params.items())
            if path:
                self.actionPath = path
            if query_params:
                self.actionParams = query_params

        self.collapseKey = _spop(data, 'collapse_key')
        self.optionalImage = _spop(data, 'i')
        self.optionalAvatarUrl = _spop(data, 'a')
        self.sound = _spop(data, 'sound')
        self.pushId = _spop(data, 'pi')
        if 'PushNotifID' in data:
            _spop(data, 'PushNotifID')

        self.pushCategory = _spop(data, 'c')

        # Идентификатор чей пост прокомментировали
        self.intendedRecipientUserId = _spop(data, 'u')
        self.sourceUserId = _spop(data, 's')
        self.igActionOverride = _spop(data, 'igo')
        self.badgeCount = _spop(data, 'bc')
        if self.badgeCount:
            self.badgeCount = BadgeCount(self.badgeCount)
        self.inAppActors = _spop(data, 'ia')
        self.suppressBadge = _spop(data, 'SuppressBadge')

        self.it = _spop(data, 'it')
        self.si = _spop(data, 'si')
        self.badge = _spop(data, 'badge')

        if data:
            raise Exception('InstagramNotification unexpected data: {data}'.format(**locals()))
