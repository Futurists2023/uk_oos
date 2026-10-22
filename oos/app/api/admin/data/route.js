import { NextResponse } from 'next/server';
import { fetchAllAdminData } from '../../../../lib/supabaseServer';

export const dynamic = 'force-dynamic';

export async function GET() {
  const data = await fetchAllAdminData();
  return NextResponse.json(data, {
    headers: {
      'Cache-Control': 'no-store, max-age=0',
      'X-Robots-Tag': 'noindex, nofollow'
    }
  });
}
