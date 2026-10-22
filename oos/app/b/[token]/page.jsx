import { notFound } from 'next/navigation';
import BrandClient from './BrandClient';
import { resolveBrandFromToken } from '../../../lib/brands';
import { fetchSingleBrandData } from '../../../lib/supabaseServer';

export const dynamic = 'force-dynamic';

export async function generateMetadata(context) {
  const params = await context.params;
  const brandObj = resolveBrandFromToken(params?.token);
  return {
    title: brandObj
      ? `${brandObj.name} — UK Retail Out-of-Stock Monitor`
      : 'Not Found',
    robots: {
      index: false,
      follow: false,
      nocache: true
    }
  };
}

export default async function BrandDashboardPage(context) {
  const params = await context.params;
  const brandObj = resolveBrandFromToken(params?.token);
  if (!brandObj) {
    notFound();
  }

  const initialData = await fetchSingleBrandData(brandObj);
  return <BrandClient initialData={initialData} />;
}
