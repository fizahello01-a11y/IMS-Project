// src/types/index.ts
// Shared TypeScript types – mirrors the backend Pydantic schemas

export type Priority = 'P0' | 'P1' | 'P2' | 'P3';
export type IncidentStatus = 'OPEN' | 'INVESTIGATING' | 'RESOLVED' | 'CLOSED';

export interface RCA {
  id: string;
  work_item_id: string;
  incident_start: string;
  incident_end: string;
  root_cause_category: string;
  fix_applied: string;
  prevention_steps: string;
  submitted_at: string;
}

export interface Incident {
  id: string;
  component_id: string;
  component_type: string;
  priority: Priority;
  status: IncidentStatus;
  title: string;
  signal_count: string;
  created_at: string;
  updated_at: string;
  mttr_minutes: number | null;
  rca: RCA | null;
}

export interface Signal {
  signal_id: string;
  component_id: string;
  component_type: string;
  error_code: string;
  message: string;
  severity: string;
  received_at: string;
  work_item_id: string;
}

export interface RCACreateForm {
  incident_start: Date;
  incident_end: Date;
  root_cause_category: string;
  fix_applied: string;
  prevention_steps: string;
}

export const ROOT_CAUSE_CATEGORIES = [
  'Network Partition',
  'Hardware Failure',
  'Software Bug',
  'Configuration Error',
  'Capacity Exhaustion',
  'Security Incident',
  'Third-party Service Failure',
  'Human Error',
  'Data Corruption',
  'Unknown',
] as const;

export const STATUS_FLOW: Record<IncidentStatus, IncidentStatus | null> = {
  OPEN:          'INVESTIGATING',
  INVESTIGATING: 'RESOLVED',
  RESOLVED:      'CLOSED',
  CLOSED:        null,
};
