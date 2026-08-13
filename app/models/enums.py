import enum


class Channel(str, enum.Enum):
    whatsapp = "whatsapp"
    simulator = "simulator"


class Language(str, enum.Enum):
    en = "en"
    ml = "ml"


class IntentType(str, enum.Enum):
    factual_claim = "factual_claim"
    image_check = "image_check"
    mixed = "mixed"
    chitchat = "chitchat"
    unclear = "unclear"


class Verdict(str, enum.Enum):
    true = "true"
    false = "false"
    misleading = "misleading"
    unverifiable = "unverifiable"
    satire = "satire"


class ConfidenceLabel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class MessageDirection(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"


class EvidenceType(str, enum.Enum):
    fact_check = "fact_check"
    web_search = "web_search"
    image_match = "image_match"
    ocr = "ocr"


class Stance(str, enum.Enum):
    supports = "supports"
    contradicts = "contradicts"
    neutral = "neutral"


class CredibilityTier(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"
    unknown = "unknown"


class FeedbackRating(str, enum.Enum):
    helpful = "helpful"
    not_helpful = "not_helpful"
    incorrect = "incorrect"


class ProviderName(str, enum.Enum):
    gemini = "gemini"
    openai = "openai"
    google_fact_check = "google_fact_check"
    google_vision = "google_vision"
    google_translate = "google_translate"
    sightengine = "sightengine"
    whatsapp = "whatsapp"


class AuditEventType(str, enum.Enum):
    consent_given = "consent_given"
    consent_revoked = "consent_revoked"
    data_deleted = "data_deleted"
    verification_created = "verification_created"
    media_deleted = "media_deleted"
