import AdminClient from './AdminClient';
import { fetchAllAdminData } from '../../lib/supabaseServer';

export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'UK OOS SaaS — Master Admin Panel (All 43 Brands)',
  robots: {
    index: false,
    follow: false
  }
};

export default async function AdminPage() {
  const initialData = await fetchAllAdminData();
  return <AdminClient initialData={initialData} />;
}
