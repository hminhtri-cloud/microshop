import type { ReactNode } from 'react';
import type { SellerStatus } from './api';

export function Icon({ name = 'bag', size = 22 }: { name?: 'bag' | 'arrow' | 'shield' | 'shop' | 'user' | 'check'; size?: number }) {
  const paths = {
    bag: <><path d="M5 7h14l1 14H4L5 7Z" /><path d="M8 7V6a4 4 0 0 1 8 0v1" /></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
    shield: <><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z" /><path d="m8 12 3 3 5-6" /></>,
    shop: <><path d="M4 10v10h16V10M3 10l2-7h14l2 7M3 10c0 3 4 3 4 0 0 3 5 3 5 0 0 3 5 3 5 0 0 3 4 3 4 0M9 20v-6h6v6" /></>,
    user: <><circle cx="12" cy="7" r="4" /><path d="M4 21v-2a8 8 0 0 1 16 0v2" /></>,
    check: <path d="m5 12 4 4L19 6" />,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

export const statuses: Record<SellerStatus, { label: string; detail: string }> = {
  pending: { label: 'Chờ duyệt', detail: 'Hồ sơ đã được gửi. Quản trị viên sẽ kiểm tra trước khi cấp quyền bán hàng.' },
  approved: { label: 'Đã duyệt', detail: 'Shop đã được duyệt và tài khoản của bạn có quyền seller.' },
  rejected: { label: 'Cần điều chỉnh', detail: 'Hồ sơ chưa được duyệt. Hãy xem lý do, cập nhật thông tin và gửi lại.' },
  suspended: { label: 'Tạm ngưng', detail: 'Quyền bán hàng đã bị tạm ngưng. Liên hệ quản trị viên để được xem xét mở lại.' },
};

export function Badge({ status }: { status: SellerStatus }) {
  return <span className={`badge ${status}`}><span />{statuses[status].label}</span>;
}

export function Notice({ children, success = false }: { children: ReactNode; success?: boolean }) {
  return <div className={`notice ${success ? 'success' : 'error'}`} role={success ? 'status' : 'alert'}>{children}</div>;
}

export function Loading() {
  return <div className="loading" role="status"><span className="spinner" /> Đang tải dữ liệu…</div>;
}

export function dateLabel(value: string | null) {
  if (!value) return '—';
  // Backend SQL DateTime currently returns naive UTC timestamps.
  const utc = /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`;
  return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(utc));
}
