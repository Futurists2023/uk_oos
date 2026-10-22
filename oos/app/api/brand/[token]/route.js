import { NextResponse } from 'next/server';
import { resolveBrandFromToken } from '../../../../lib/brands';
import { fetchSingleBrandData } from '../../../../lib/supabaseServer';

export const dynamic = 'force-dynamic';

export async function GET(request, context) {
  const params = await context.params;
  const brandObj = resolveBrandFromToken(params?.token);
  if (!brandObj) {
    return NextResponse.json({ error: 'Invalid or expired brand link' }, { status: 404 });
  }
  const data = await fetchSingleBrandData(brandObj);
  return NextResponse.json(data, {
    headers: {
      'Cache-Control': 'no-store, max-age=0',
      'X-Robots-Tag': 'noindex, nofollow'
    }
  });
}
