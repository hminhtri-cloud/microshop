const TOKEN_KEY = 'microshop.access-token';

export const session = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (value: string) => sessionStorage.setItem(TOKEN_KEY, value),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  status: number;
  code: string;
  details: unknown;
  requestId: string | null;

  constructor(status: number, message: string, code = 'UNKNOWN_ERROR', details: unknown = null, requestId: string | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

const messages: Record<string, string> = {
  'Invalid email or password': 'Email hoặc mật khẩu chưa đúng.',
  'Invalid or expired access token': 'Phiên đăng nhập đã hết hạn. Anh/chị vui lòng đăng nhập lại.',
  'Email already registered': 'Email này đã được đăng ký.',
  'Username already taken': 'Tên người dùng đã được sử dụng.',
  'Username or email already registered': 'Tên người dùng hoặc email đã được đăng ký.',
  'Insufficient permissions': 'Tài khoản không có quyền thực hiện thao tác này.',
  'Invalid seller status transition': 'Trạng thái hồ sơ đã thay đổi. Vui lòng tải lại danh sách.',
  'An application already exists; contact admin if suspended': 'Hồ sơ đã tồn tại. Nếu bị tạm ngưng, vui lòng liên hệ quản trị viên.',
  'An application already exists': 'Hồ sơ đăng ký đã tồn tại.',
  'Product is blocked by an administrator': 'Sản phẩm đang bị quản trị viên khóa. Vui lòng liên hệ quản trị viên.',
  'Product not found': 'Sản phẩm không còn hiển thị hoặc đã bị gỡ.',
};

const codeMessages: Record<string, string> = {
  INVALID_CREDENTIALS: 'Email hoặc mật khẩu chưa đúng.',
  AUTHENTICATION_REQUIRED: 'Phiên đăng nhập đã hết hạn. Anh/chị vui lòng đăng nhập lại.',
  FORBIDDEN: 'Tài khoản không có quyền thực hiện thao tác này.',
  INSUFFICIENT_STOCK: 'Sản phẩm không đủ số lượng để đặt hàng.',
  ORDER_NOT_FOUND: 'Không tìm thấy đơn hàng.',
  IDEMPOTENCY_CONFLICT: 'Yêu cầu đặt hàng đã dùng mã retry khác nội dung.',
  INVALID_STATUS_TRANSITION: 'Trạng thái hiện tại không cho phép thao tác này.',
  SERVICE_UNAVAILABLE: 'Dịch vụ tạm thời chưa sẵn sàng. Vui lòng thử lại.',
};

type ErrorBody = {
  code?: unknown;
  message?: unknown;
  details?: unknown;
  request_id?: unknown;
  detail?: unknown;
};

function errorText(body: ErrorBody | null): { code: string; message: string; details: unknown; requestId: string | null } {
  const detail = body?.detail;
  if (typeof body?.code === 'string' && typeof body.message === 'string') {
    return {
      code: body.code,
      message: codeMessages[body.code] || body.message,
      details: body.details ?? null,
      requestId: typeof body.request_id === 'string' ? body.request_id : null,
    };
  }
  if (typeof detail === 'string') {
    return { code: 'LEGACY_ERROR', message: messages[detail] || detail, details: null, requestId: null };
  }
  if (Array.isArray(detail)) {
    return {
      code: 'VALIDATION_ERROR',
      message: detail.map((item: { loc?: string[]; msg?: string }) => `${item.loc?.slice(1).join('.') || 'Dữ liệu'}: ${item.msg || 'Không hợp lệ'}`).join(' · '),
      details: detail,
      requestId: null,
    };
  }
  return { code: 'UNKNOWN_ERROR', message: 'Máy chủ gặp lỗi. Vui lòng thử lại sau.', details: null, requestId: null };
}

export async function request<T>(path: string, options: RequestInit = {}, authenticated = true): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set('Content-Type', 'application/json');
  const token = authenticated ? session.get() : null;
  if (token) headers.set('Authorization', `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      headers,
      signal: options.signal ?? AbortSignal.timeout(15000),
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError(0, 'Không kết nối được máy chủ. Kiểm tra backend và thử lại.', 'NETWORK_ERROR');
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && token) {
      session.clear();
      window.dispatchEvent(new Event('microshop:unauthorized'));
    }
    const error = errorText(data as ErrorBody | null);
    throw new ApiError(response.status, error.message, error.code, error.details, error.requestId);
  }
  return data as T;
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Đã có lỗi xảy ra. Vui lòng thử lại.';
}
