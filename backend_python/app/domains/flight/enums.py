"""Flight domain enums.

Business value enums specific to flight operations and booking.
"""

from enum import StrEnum

# ==============================================================================
# API ENVIRONMENT ENUMS
# ==============================================================================


class FlightAPIEnvironment(StrEnum):
    """Flight API environment values.

    Used by flight service providers (FlightLogic, Amadeus, etc.)
    to specify test vs production environments.
    """

    TEST = "Test"
    PRODUCTION = "Production"


# ==============================================================================
# JOURNEY & BOOKING ENUMS
# ==============================================================================


class JourneyType(StrEnum):
    """Journey types supported by FlightLogic."""

    ONE_WAY = "OneWay"
    RETURN = "Return"
    CIRCLE = "Circle"


class CabinClass(StrEnum):
    """Cabin classes available for flight search."""

    ECONOMY = "Economy"
    BUSINESS = "Business"
    FIRST = "First"
    PREMIUM_ECONOMY = "PremiumEconomy"


class BookingStatus(StrEnum):
    """Booking status from FlightLogic API.

    These values come directly from the FlightLogic booking response.
    """

    CONFIRMED = "CONFIRMED"  # FlightLogic API uses uppercase
    PENDING = "Pending"  # FlightLogic API value
    BOOKED = "Booked"  # FlightLogic API value

    # Additional statuses for internal use
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    TICKETED = "Ticketed"


class CarrierType(StrEnum):
    """Carrier type for flight bookings.

    - LCC: Low Cost Carrier (budget airlines, direct booking)
    - GDS: Global Distribution System (traditional airlines, aggregated booking)
    """

    LCC = "LCC"
    GDS = "GDS"


class FareType(StrEnum):
    """Fare type enumeration.

    Maps to FlightLogic API fare types:
    - PRIVATE & PUBLIC: GDS (Global Distribution System) bookings
    - WEB_FARE: LCC (Low Cost Carrier) bookings
    """

    PRIVATE = "Private"
    PUBLIC = "Public"
    WEB_FARE = "WebFare"

    @property
    def is_lcc(self) -> bool:
        """Check if this fare type is LCC (Low Cost Carrier).

        Returns:
            True if WebFare (LCC), False if Private/Public (GDS)
        """
        return self == FareType.WEB_FARE

    @property
    def is_gds(self) -> bool:
        """Check if this fare type is GDS (Global Distribution System).

        Returns:
            True if Private or Public (GDS), False if WebFare (LCC)
        """
        return self in (FareType.PRIVATE, FareType.PUBLIC)

    @property
    def carrier_type(self) -> "CarrierType":
        """Get the carrier type enum.

        Returns:
            CarrierType.LCC for WebFare, CarrierType.GDS for Private/Public
        """
        return CarrierType.LCC if self.is_lcc else CarrierType.GDS


class TicketType(StrEnum):
    """Ticket type enumeration."""

    E_TICKET = "eTicket"
    PAPER_TICKET = "PaperTicket"


# ==============================================================================
# PASSENGER ENUMS
# ==============================================================================


class PassengerType(StrEnum):
    """Passenger type enumeration."""

    ADULT = "ADT"
    CHILD = "CHD"
    INFANT = "INF"


class PassportRequirement(StrEnum):
    """Passport requirement levels for bookings.

    Custom business logic based on IsPassportMandatory and
    IsPassportFullDetailsMandatory from FlightLogic API.
    """

    NOT_REQUIRED = "not_required"  # Domestic flights, passport not needed
    BASIC_REQUIRED = "basic_required"  # Only passport number and expiry needed
    FULL_REQUIRED = "full_required"  # All passport details including issue date/country


# ==============================================================================
# TRAVEL PREFERENCES - Moved from user domain as they're flight-specific
# ==============================================================================


class TravelClass(StrEnum):
    """Preferred travel class.

    Custom business logic - lowercase for internal use.
    FlightLogic API uses: Economy, PremiumEconomy, Business, First
    """

    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class SeatPreference(StrEnum):
    """Seat preference options.

    Custom business logic - not from FlightLogic API.
    """

    WINDOW = "window"
    AISLE = "aisle"
    MIDDLE = "middle"
    NO_PREFERENCE = "no_preference"


class MealPreference(StrEnum):
    """Meal preference options.

    Custom business logic - human-readable names.
    FlightLogic API uses IATA meal codes (see MealCode enum).
    """

    STANDARD = "standard"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    KOSHER = "kosher"
    HALAL = "halal"
    GLUTEN_FREE = "gluten_free"
    DIABETIC = "diabetic"


# ==============================================================================
# BAGGAGE & SERVICE ENUMS
# ==============================================================================


class BaggageUnit(StrEnum):
    """Baggage measurement units and allowance types."""

    PIECE = "P"  # Number of pieces (also used as "PIECE" in allowance)
    KILOGRAM = "K"  # Weight in kilograms (maps to "WEIGHT" in allowance)
    STANDARD = "SB"  # Standard baggage (also "STANDARD" in allowance)
    WEIGHT = "WEIGHT"  # Weight-based allowance (alternative format)


# ==============================================================================
# FARE CLASS ENUMS
# ==============================================================================


class LCCBookingClass(StrEnum):
    """Booking class descriptions for LCC (Low Cost Carrier) fares.

    Used when ResBookDesigText is present (WebFare/LCC bookings).
    These don't have RBD codes.

    Note: "Lowest Fare" is verified from FlightLogic API.
    Other values are common LCC fare types but not all verified.
    """

    LOWEST_FARE = "Lowest Fare"  # Verified from FlightLogic API
    VALUE = "Value"
    FLEX = "Flex"
    PREMIUM = "Premium"
    BUSINESS_FLEX = "Business Flex"
    SAVER = "Saver"
    FLEXI_SAVER = "Flexi Saver"
    SUPER_SAVER = "Super Saver"
    ECONOMY_BASIC = "Economy Basic"
    ECONOMY_STANDARD = "Economy Standard"
    ECONOMY_FLEX = "Economy Flex"


class TicketStatus(StrEnum):
    """Ticket status from FlightLogic API.

    TktInProcess is the actual value from FlightLogic trip details response.
    """

    IN_PROCESS = "TktInProcess"  # FlightLogic API value
    TICKETED = "Ticketed"
    CANCELLED = "Cancelled"
    NOT_ISSUED = "NotIssued"


class PNRStatus(StrEnum):
    """PNR status enumeration.

    Custom business logic - not from FlightLogic API.
    """

    ACTIVE = "Active"
    CANCELLED = "Cancelled"
    EXPIRED = "Expired"
    CONFIRMED = "Confirmed"
    PENDING = "Pending"
    WAITLISTED = "Waitlisted"


class RequiredBookingField(StrEnum):
    """Required booking field enumeration.

    Custom business logic - not from FlightLogic API.
    """

    PASSPORT = "Passport"
    DOB = "DOB"
    NATIONALITY = "Nationality"
    VISA_INFO = "VisaInfo"
    FREQUENT_FLYER = "FrequentFlyer"


class FrequentFlyerTier(StrEnum):
    """Frequent flyer tier enumeration.

    Standard industry tiers - not from FlightLogic API.
    """

    BASIC = "Basic"
    SILVER = "Silver"
    GOLD = "Gold"
    PLATINUM = "Platinum"
    DIAMOND = "Diamond"


class ServiceBehavior(StrEnum):
    """Service behavior enumeration."""

    PER_PAX = "PER_PAX"
    GROUP_PAX = "GROUP_PAX"
    PER_PAX_OUTBOUND = "PER_PAX_OUTBOUND"
    PER_PAX_INBOUND = "PER_PAX_INBOUND"
    PER_PAX_SEGMENT = "PER_PAX_SEGMENT"
    PER_PAX_SEGMENT_OUTBOUND = "PER_PAX_SEGMENT_OUTBOUND"
    PER_PAX_SEGMENT_INBOUND = "PER_PAX_SEGMENT_INBOUND"
    GROUP_PAX_OUTBOUND = "GROUP_PAX_OUTBOUND"
    GROUP_PAX_INBOUND = "GROUP_PAX_INBOUND"


class CheckInLocation(StrEnum):
    """Check-in location enumeration."""

    AIRPORT = "AIRPORT"
    ONLINE = "ONLINE"
    COUNTER = "COUNTER"
    BOTH = "BOTH"


class ServiceType(StrEnum):
    """Service category enumeration.

    Custom categorization for extra services.
    FlightLogic uses DynamicBaggage, DynamicMeal, DynamicSeat.
    """

    BAGGAGE = "BAGGAGE"
    MEAL = "MEAL"
    SEAT = "SEAT"
    ASSISTANCE = "ASSISTANCE"
    INSURANCE = "INSURANCE"
    PRIORITY = "PRIORITY"
    OTHER = "OTHER"


class MealCode(StrEnum):
    """IATA standard meal code enumeration."""

    VGML = "VGML"  # Vegan Meal
    AVML = "AVML"  # Asian Vegetarian Meal
    HNML = "HNML"  # Hindu Meal
    KSML = "KSML"  # Kosher Meal
    LCML = "LCML"  # Low Calorie Meal
    NLML = "NLML"  # Non-Lactose Meal
    SFML = "SFML"  # Seafood Meal
    FPML = "FPML"  # Fruit Platter Meal
    GFML = "GFML"  # Gluten Intolerant Meal
    DBML = "DBML"  # Diabetic Meal
    VLML = "VLML"  # Vegetarian Lacto-Ovo Meal
    MOML = "MOML"  # Muslim Meal
    CHML = "CHML"  # Child Meal
    BBML = "BBML"  # Baby Meal
    BLML = "BLML"  # Bland Meal
    LSML = "LSML"  # Low Sodium Meal
    LFML = "LFML"  # Low Fat Meal
    VJML = "VJML"  # Vegetarian Jain Meal
    VOML = "VOML"  # Vegetarian Oriental Meal
    RVML = "RVML"  # Raw Vegetarian Meal


class MarriageGroup(StrEnum):
    """Marriage group enumeration."""

    O = "O"  # Open
    I = "I"  # Inside
    M = "M"  # Married


class FareRuleCategory(StrEnum):
    """Fare rule category enumeration - matches FlightLogic API values."""

    RULE_APPLICATION = "RULE APPLICATION AND OTHER CONDITIONS"
    ELIGIBILITY = "ELIGIBILITY"


class FlightStatus(StrEnum):
    """Flight status codes.

    Standard IATA flight status codes.
    Not specific to FlightLogic API.
    """

    ON_TIME = "ON"  # On Time
    DELAYED = "DL"  # Delayed
    CANCELLED = "CX"  # Cancelled
    DIVERTED = "DV"  # Diverted
    BOARDING = "BD"  # Boarding
    CLOSED = "CL"  # Closed
    DEPARTED = "DP"  # Departed
    ARRIVED = "AR"  # Arrived


class CabinClassText(StrEnum):
    """Cabin class text enumeration.

    Used for LCC/WebFare bookings from CabinClassText field.
    """

    REGULAR_FARE = "REGULAR FARE"  # Verified from FlightLogic API
    FLEX = "Flex"
    LIGHT = "Light"
    STANDARD = "Standard"
    PREMIUM = "Premium"


class PassengerTitle(StrEnum):
    """Passenger title options for flight bookings."""

    MR = "Mr"
    MRS = "Mrs"
    MS = "Ms"
    MISS = "Miss"
    MASTER = "Master"
