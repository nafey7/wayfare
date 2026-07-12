export type TripType = 'oneWay' | 'roundTrip' | 'multiCity';

export type TravelStyle =
  | 'solo'
  | 'friends'
  | 'family'
  | 'romantic'
  | 'business';

export type BudgetMindset = 'comfort' | 'bestValue' | 'premium' | 'luxury';

export type CabinClass = 'economy' | 'premiumEconomy' | 'business' | 'first';

export interface Passengers {
  adults: number;
  children: number;
  infants: number;
}

export interface DateRange {
  outbound: string | null;
  return: string | null;
}

export interface TripMaster {
  destination: string | null;
  origin: string | null;
  dates: DateRange;
  passengers: Passengers;
  tripType: TripType;
  travelStyle: TravelStyle | null;
  budgetMindset: BudgetMindset | null;
  budgetAmount: number | null;
}
