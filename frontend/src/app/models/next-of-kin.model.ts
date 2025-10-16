export interface NextOfKinContact {
  id: string;
  relationship: string;
  full_name: string;
  phone_number: string;
  email?: string;
  address?: string;
  is_primary: boolean;
  is_emergency_contact: boolean;
  created_at: string;
  updated_at: string;
}

export interface NextOfKinCreate {
  relationship: string;
  full_name: string;
  phone_number: string;
  email?: string;
  address?: string;
  is_primary?: boolean;
  is_emergency_contact: boolean;
}

export interface NextOfKinUpdate {
  relationship?: string;
  full_name?: string;
  phone_number?: string;
  email?: string;
  address?: string;
  is_primary?: boolean;
  is_emergency_contact?: boolean;
}

export const RELATIONSHIP_OPTIONS = [
  'Spouse',
  'Parent', 
  'Sibling',
  'Child',
  'Friend',
  'Relative',
  'Colleague',
  'Other'
] as const;

export type RelationshipType = typeof RELATIONSHIP_OPTIONS[number];
