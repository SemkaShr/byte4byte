import math

class Session:
    def __init__(self, data=None):
        if data != None:
            self.usable = self.load(data)
    
    def getFeatures(self):
        d = self.data[-1]["data"]

        duration = min(d.get("duration", 0.0), 30.0)
        hidden = min(d.get("hidden_seconds", 0.0), duration)
        fid = d.get("first_interaction_delay")
        if fid is None:
            fid = duration

        mouse_moves = d.get("mouse_move_count", 0)
        clicks = d.get("click_count", 0)
        scrolls = d.get("scroll_events", 0)
        keys = d.get("key_events", 0)

        interaction_count = mouse_moves + clicks + scrolls + keys

        interaction_types = [
            mouse_moves > 0,
            clicks > 0,
            scrolls > 0,
            keys > 0
        ]
        probs = [1 / sum(interaction_types)] * sum(interaction_types) if sum(interaction_types) else []
        interaction_entropy = -sum(p * math.log(p) for p in probs) if probs else 0.0

        features = {
            "label": self.label,
            "duration": duration,
            "active_ratio": d.get("active_ratio", 0.0),
            "first_interaction_delay": fid,
            "focus_count": d.get("focus_count", 0),
            "hidden_seconds": hidden,
            "pct_time_hidden": hidden / duration if duration > 0 else 0.0,

            "mouse_move_count": mouse_moves,
            "mouse_total_distance": d.get("mouse_total_distance", 0.0),
            "mouse_avg_speed": d.get("mouse_avg_speed", 0.0),
            "mouse_speed_variance": d.get("mouse_speed_variance", 0.0),
            "mouse_moves_per_sec": mouse_moves / duration if duration > 0 else 0.0,
            "distance_per_move": d.get("mouse_total_distance", 0.0) / max(1, mouse_moves),

            "click_count": clicks,
            "clicks_per_sec": clicks / duration if duration > 0 else 0.0,
            "avg_click_delay": d.get("avg_click_delay", 0.0),

            "scroll_events": scrolls,
            "scrolls_per_sec": scrolls / duration if duration > 0 else 0.0,
            "max_scroll_depth": d.get("max_scroll_depth", 0.0),
            "scroll_avg_speed": d.get("scroll_avg_speed", 0.0),

            "key_events": keys,
            "key_avg_dwell": d.get("key_avg_dwell", 0.0),

            "interaction_count": interaction_count,
            "interaction_entropy": interaction_entropy,

            "had_mouse": int(mouse_moves > 0),
            "had_clicks": int(clicks > 0),
            "had_scroll": int(scrolls > 0),
            "had_keyboard": int(keys > 0),
        }

        return features

    
    def load(self, data):
        self.data = data['data']
        if(len(self.data) <= 1 or len(self.data) > 10):
            return False
        
        self.ip = data['ray']['request']['ip']
        self.score = data['ray']['score']
        self.scoreLogs = data['ray'].get('scoreLogs', [])
        self.userAgent = data['ray']['request']['user-agent']
        self.id = self.data[0]['session']
        self.rayID = data['ray']['id']
        self.label = data['ray'].get('requestType', 'human')
        
        if self.data[-1]['event'] == 'session_end' and self.data[-2]['event'] == 'session_end':
            self.data.pop(-1)
            
        return True