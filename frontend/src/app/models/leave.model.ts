export interface Document {
  id?: number;
  name: string;
  fileType: string;
  size: number;
  file?: File;  // For client-side use
  url?: string; // For server-side stored files
  uploadDate: Date;
}
export interface Leave {
  id: string;
  employeeId: string;
  leaveType: string;
  startDate: Date;
  endDate: Date;
  comments: string;
  status: 'pending' | 'approved' | 'rejected' | 'cancelled';
  createdAt: Date;
  updatedAt: Date;
  documents: Document[];
}

export interface LeaveBalance {
  id: string;
  user_id: string;
  leave_type: string;
  balance_days: number;
  total_days: number;
  updated_at: Date;
}

export interface NotificationConfig {
  message: string;
  type: 'success' | 'info' | 'warning' | 'error';
  duration: number;
}
