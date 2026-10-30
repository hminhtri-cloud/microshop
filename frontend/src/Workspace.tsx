import { Link, NavLink, Outlet } from 'react-router-dom';

import { useAuth } from './auth';
import { Icon } from './ui';

export function WorkspaceLayout({ admin = false }: { admin?: boolean }) {
  const { user } = useAuth();
  const seller = user?.role === 'seller';
  return <div className="workspace-shell container"><aside className="workspace-sidebar" aria-label={admin ? 'Menu quản trị' : 'Menu kênh người bán'}>
    <span className="eyebrow">{admin ? 'QUẢN TRỊ SÀN' : seller ? 'SELLER CENTER' : 'TRỞ THÀNH NGƯỜI BÁN'}</span>
    <h2>{admin ? 'Quản trị' : seller ? 'Kênh người bán' : 'Bắt đầu mở shop'}</h2>
    <nav className="workspace-nav" aria-label={admin ? 'Điều hướng quản trị' : 'Điều hướng người bán'}>
      <NavLink to={admin ? '/admin' : '/seller'} end>{admin ? 'Hồ sơ người bán' : 'Hồ sơ cửa hàng'}</NavLink>
      {admin ? <NavLink to="/admin/products">Kiểm duyệt sản phẩm</NavLink> : seller && <NavLink to="/seller/products">Sản phẩm của tôi</NavLink>}
      {(admin || seller) && <span className="nav-upcoming">{admin ? 'Quản lý đơn hàng' : 'Đơn bán'} <small>Sắp có</small></span>}
    </nav>
    <div className="workspace-sidebar-footer"><Link to="/products"><Icon name="arrow" size={16} /> Quay lại mua sắm</Link><p>{admin ? 'Quản lý cộng đồng và nội dung trên MicroShop.' : seller ? 'Trang quản lý cửa hàng, tách biệt với khu mua sắm.' : 'Khi được duyệt, bạn sẽ có thêm trang quản lý sản phẩm.'}</p></div>
  </aside><div className="workspace-content"><Outlet /></div></div>;
}
