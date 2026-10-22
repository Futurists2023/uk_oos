import './globals.css';

export const metadata = {
  title: 'UK Retail Out-of-Stock Monitor',
  description: 'Live UK Stockist & Shelf Availability Tracker',
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: {
      index: false,
      follow: false,
      noimageindex: true
    }
  }
};

export default function RootLayout({ children }) {
  return (
    <html lang="en-GB">
      <body>{children}</body>
    </html>
  );
}
