import { MarketDesk } from '../components/MarketDesk';

export type DashboardSession = {
  sub: string;
  role: string;
};

export function DashboardScreen({ token, session, onLogout }: { token: string; session: DashboardSession; onLogout: () => void }) {
  return <MarketDesk token={token} session={session} onLogout={onLogout} />;
}
