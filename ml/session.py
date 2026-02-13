import math

import pandas as pd
from config import MODEL

class Session:
    def __init__(self, data=None):
        self.label = None
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

        # msd = d.get("max_scroll_depth", 0.0)

        # features = {
        #     "label": self.label,
        #     "duration": math.log(duration),
        #     "active_ratio": d.get("active_ratio", 0.0),
        #     "first_interaction_delay": math.log(fid) if fid > 0 else 0,
        #     "focus_count": d.get("focus_count", 0),
        #     "hidden_seconds": math.log(hidden) if hidden > 0 else 0,
        #     "pct_time_hidden": hidden / duration if duration > 0 else 0.0,

        #     "mouse_move_count": mouse_moves,
        #     "mouse_total_distance": d.get("mouse_total_distance", 0.0),
        #     "mouse_avg_speed": d.get("mouse_avg_speed", 0.0),
        #     "mouse_speed_variance": d.get("mouse_speed_variance", 0.0),
        #     "mouse_moves_per_sec": mouse_moves / duration if duration > 0 else 0.0,
        #     "distance_per_move": d.get("mouse_total_distance", 0.0) / max(1, mouse_moves),

        #     "click_count": clicks,
        #     "clicks_per_sec": clicks / duration if duration > 0 else 0.0,
        #     "avg_click_delay": d.get("avg_click_delay", 0.0),

        #     "scroll_events": scrolls,
        #     "scrolls_per_sec": scrolls / duration if duration > 0 else 0.0,
        #     "max_scroll_depth": math.log(msd) if msd > 0 else 0,
        #     "scroll_avg_speed": d.get("scroll_avg_speed", 0.0),

        #     "key_events": keys,
        #     "key_avg_dwell": d.get("key_avg_dwell", 0.0),

        #     "interaction_count": interaction_count,
        #     "interaction_entropy": interaction_entropy,

        #     "had_mouse": int(mouse_moves > 0),
        #     "had_clicks": int(clicks > 0),
        #     "had_scroll": int(scrolls > 0),
        #     "had_keyboard": int(keys > 0),
        # }
        
        import numpy as np

        features = {
            "label": self.label,

            # ---- Time (log) ----
            "log_duration": np.log1p(duration),
            "log_first_interaction_delay": np.log1p(fid),
            "log_hidden_seconds": np.log1p(hidden),
            "log_avg_click_delay": np.log1p(d.get("avg_click_delay", 0.0)),
            "log_key_avg_dwell": np.log1p(d.get("key_avg_dwell", 0.0)),

            # ---- Ratios (keep linear) ----
            "active_ratio": d.get("active_ratio", 0.0),
            "pct_time_hidden": hidden / duration if duration > 0 else 0.0,
            "interaction_entropy": interaction_entropy,

            # ---- Counts (log) ----
            "log_mouse_move_count": np.log1p(mouse_moves),
            "log_click_count": np.log1p(clicks),
            "log_scroll_events": np.log1p(scrolls),
            "log_key_events": np.log1p(keys),
            "log_focus_count": np.log1p(d.get("focus_count", 0)),
            "log_interaction_count": np.log1p(interaction_count),

            # ---- Per-second rates (optional log) ----
            "log_mouse_moves_per_sec": np.log1p(mouse_moves / duration) if duration > 0 else 0.0,
            "log_clicks_per_sec": np.log1p(clicks / duration) if duration > 0 else 0.0,
            "log_scrolls_per_sec": np.log1p(scrolls / duration) if duration > 0 else 0.0,

            # ---- Distances (log) ----
            "log_mouse_total_distance": np.log1p(d.get("mouse_total_distance", 0.0)),
            "log_distance_per_move": np.log1p(
                d.get("mouse_total_distance", 0.0) / max(1, mouse_moves)
            ),
            "log_max_scroll_depth": np.log1p(d.get("max_scroll_depth", 0.0)),

            # ---- Speeds (log if heavy tail) ----
            "log_mouse_avg_speed": np.log1p(d.get("mouse_avg_speed", 0.0)),
            "log_mouse_speed_variance": np.log1p(d.get("mouse_speed_variance", 0.0)),
            "log_scroll_avg_speed": np.log1p(d.get("scroll_avg_speed", 0.0)),

            # ---- Binary ----
            "had_mouse": int(mouse_moves > 0),
            "had_clicks": int(clicks > 0),
            "had_scroll": int(scrolls > 0),
            "had_keyboard": int(keys > 0),
            
            "moves_per_click": mouse_moves / max(1, clicks),
            "clicks_per_scroll": clicks / max(1, scrolls),
            "keys_per_click": keys / max(1, clicks),
            
            "speed_variation_ratio": d.get("mouse_speed_variance", 0.0) / 
                         (d.get("mouse_avg_speed", 1e-6) + 1e-6),
                         
            "duration_per_interaction": duration / max(1, interaction_count),
            "distance_per_second": d.get("mouse_total_distance", 0.0) / max(1, duration),
            
            "clicks_without_scroll": int(clicks > 0 and scrolls == 0)
        }
        

        
        features.update({
            "distance_per_click": d.get("mouse_total_distance", 0.0) / max(1, clicks),
            "distance_per_scroll": d.get("mouse_total_distance", 0.0) / max(1, scrolls),
        })
        
        features.update({
            "interaction_per_mouse_move": interaction_count / max(1, mouse_moves),
            "entropy_x_density": interaction_entropy *
                                (interaction_count / max(1, duration)),
        })


        return features

    
    def load(self, data):
        self.data = data['data']
        
        self.ip = data['ray']['request']['ip']
        self.score = data['ray']['score']
        self.scoreLogs = data['ray'].get('scoreLogs', [])
        self.ja4Fingerprint = data['ray']['request']['ja4_fingerprint']
        self.userAgent = data['ray']['request']['user-agent']
        self.id = self.data[0]['session']
        self.rayID = data['ray']['id']
        self.label = data['ray'].get('requestType', 'human')
        
        if(len(self.data) <= 1 or len(self.data) > 10):
            return False
        
        if self.data[-1]['data'].get("duration", 0.0) <= 0:
            return False
        
        if self.data[-1]['event'] == 'session_end' and self.data[-2]['event'] == 'session_end':
            self.data.pop(-1)
            
        return True
    
    def predict(self, data=None):
        if data != None:
            self.data = [data]
        data = pd.DataFrame([self.getFeatures()]).drop('label', axis=1)
        proba = MODEL.predict_proba(data)[0]
        return proba