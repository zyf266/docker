/** 与后端 api/deps.is_admin_role 对齐 */
export const isAdminRole = (role) =>
  ['superuser', 'admin', 'root'].includes(String(role || '').toLowerCase())

export const readStoredUser = () => {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null')
  } catch (_) {
    return null
  }
}
