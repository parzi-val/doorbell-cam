
import numpy as np
from backend.config.config import IntentConfig
from backend.utils.smoothing import EMASmoother

class IntentEngine:
    def __init__(self):
        self.config = IntentConfig
        self.intent_smoother = EMASmoother(IntentConfig.INTENT_ALPHA)
        self.current_score = 0.0
        self.current_level = "CALM"

    def normalize(self, signals):
        """
        Normalize signals to [0, 1] range based on configured max values.
        """
        norm_signals = {}
        for key, max_val in self.config.NORM_MAX.items():
            val = signals.get(key, 0.0)
            norm_val = min(val / max_val, 1.0)
            norm_signals[key] = max(0.0, norm_val) # Ensure >= 0
        return norm_signals

    def _normalize_presence(self, raw_presence):
        """
        Piecewise linear ramp for presence.
        < MIN -> 0
        MIN..MAX -> 0..1
        > MAX -> 1
        """
        min_p = self.config.PRESENCE_RAMP_MIN
        max_p = self.config.PRESENCE_RAMP_MAX
        
        if raw_presence < min_p:
            return 0.0
        elif raw_presence > max_p:
            return 1.0
        else:
            return (raw_presence - min_p) / (max_p - min_p)

    def classify_level(self, score):
        if score < self.config.TH_CALM:
            return "CALM"
        elif score < self.config.TH_UNUSUAL:
            return "UNUSUAL"
        elif score < self.config.TH_SUSPICIOUS:
            return "SUSPICIOUS"
        else:
            return "THREAT"

    def update(self, signals):
        """
        Compute intent score and level from raw signals.
        :param signals: dict of raw signal values
        :return: (score, level, normalized_signals)
        """
        norm = self.normalize(signals)
        
        # Weighted Fusion (excluding presence first to calculate gating)
        other_score = 0.0
        total_other_weight = 0.0
        
        # Calculate score from non-presence signals
        for key, weight in self.config.WEIGHTS.items():
            if key == "presence_s": continue # Ensure we don't double count if user put it there
            other_val = norm.get(key, 0.0)
            other_score += other_val * weight
            total_other_weight += weight
            
        # Presence Logic
        raw_presence = signals.get("presence_s", 0.0)
        presence_val = self._normalize_presence(raw_presence)
        norm["presence_s"] = presence_val # Update for return

        # Gating: If other signals are high, presence matters more.
        # Base weight for presence? Let's assume a base weight implicit or defined.
        # Since "presence_s" is NOT in the WEIGHTS dict in config (I should check), 
        # I need to handle it. 
        # Actually I didn't verify if presence_s is in WEIGHTS. 
        # In my previous config edit, I didn't add it. Good.
        
        # Let's define a base influence. 
        # IF total score is roughly [0, 1], lets say presence adds to it.
        
        # Gating Factor: 
        # effective_presence_weight = BASE * (1 + other_score * GATING_FACTOR)
        # Let's pick a BASE weight, say 0.1 similar to others.
        BASE_PRESENCE_WEIGHT = 0.1
        
        gated_weight = BASE_PRESENCE_WEIGHT * (1 + other_score * self.config.PRESENCE_GATING_FACTOR)
        
        raw_score = other_score + (presence_val * gated_weight)
        
        # Clip raw score to [0, 1]
        raw_score = min(max(raw_score, 0.0), 1.0)

        # Smooth
        self.current_score = self.intent_smoother.update(raw_score)
        
        # Classify
        self.current_level = self.classify_level(self.current_score)

        return self.current_score, self.current_level, norm
