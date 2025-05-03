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
  id: number;
  employeeId: number;
  leaveType: string;
  startDate: Date;
  endDate: Date;
  reason: string;
  status: 'pending' | 'approved' | 'rejected' | 'cancelled';
  createdAt: Date;
  updatedAt: Date;
  documents: Document[];
}

export interface LeaveBalance {
  type: string;
  available: number;
  total: number;
}

export interface NotificationConfig {
  message: string;
  type: 'success' | 'info' | 'warning' | 'error';
  duration: number;
}
