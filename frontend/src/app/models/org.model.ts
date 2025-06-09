export interface OrgUnit {
  id: string;
  name: string;
  parent_unit_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface TreeItem {
  id: string;
  name: string;
  type?: 'unit' | 'role';
  parent_unit_id?: string;
  expanded?: boolean;
  children?: TreeItem[];
  managers?: any[];
  users?: any[];
  is_manager?: boolean;
  role_title?: string;
  role_band?: string;
  email?: string;
}

export interface OrgNode {
  id: string;
  name: string;
  type: 'unit' | 'role' | 'user';
  parent_id?: string;
  children?: OrgNode[];
  data?: any;
} 