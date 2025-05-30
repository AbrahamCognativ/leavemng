export interface OrgUser {
  id: string;
  name: string;
}

export interface OrgNode {
  id: string;
  name?: string;
  title?: string;
  type: 'unit' | 'role';
  is_manager?: boolean;
  users?: OrgUser[];
  children: OrgNode[];
}

// Existing org unit interface (simplified version that matches backend)
export interface OrgChartResponse {
  id: string;
  name: string;
  type: string;
  children: OrgNode[];
}
