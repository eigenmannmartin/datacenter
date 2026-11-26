# Rechenbox 5-year plan model, CHF excl. VAT. Run: python3 docs/model.py
# v4 (2026-11-26): Start = one small-form-factor node; Business and Pro = the same 3-node cluster
# in a 10-inch rack, differing only in support (and price). Off-site backup copy is an optional add-on.
# Compares ways to finance the hardware. Every number is an assumption; change it and re-run.

# ---- Hardware bill of materials per box (estimates, Nov 2026 prices) ----
NODE = {  # one small-form-factor node (MS-A2 class: 16 cores, 2x10G SFP+, 3x M.2/U.2)
    'single': dict(barebone=850, ram=800,  data_ssd=2*500, boot=60),  # 64 GB RAM, 2x 3.84 TB PLP NVMe (ZFS mirror)
    'M':      dict(barebone=850, ram=1300, data_ssd=2*500, boot=60),  # 96 GB RAM, 2x 3.84 TB PLP NVMe (Ceph)
}
SHARED = {
    'single':  dict(cabinet=300, switch=150, firewall=600, ups_lithium=450, ip_kvm=100,
                    lte_router=250, smart_plug=100, backup_node=900, cables=50),
    'cluster': dict(cabinet=500, switch=250, firewall=600, ups_lithium=600, ip_kvm=300,
                    lte_router=250, switched_pdu=250, backup_node=1200, cables=150),
}
STORAGE_ADDON = dict(price=190, hw=3 * 2 * 500, tb=6)  # +6 TB usable: bigger drives in all 3 nodes
def node_cost(size): return sum(NODE[size].values())

# hours = expected staff hours per month (monitoring follow-up, incidents, reviews/drills).
# Customers make their own changes in the box's web portal, so no change hours are included.
# extra = tier-specific monthly cost (Pro: share of the 24/7 on-call allowance)
tiers = {
# offsite = monthly price of the optional Swiss off-site backup copy for this plan's data volume
    'Start':    dict(nodes=1, size='single', box='single',  price=790,  setup=2900, tb=3,  offsite=90,  hours=1.5, extra=0,  mix=0.40),
    'Business': dict(nodes=3, size='M',      box='cluster', price=1890, setup=6900, tb=6,  offsite=140, hours=2.5, extra=0,  mix=0.40),
    'Pro':      dict(nodes=3, size='M',      box='cluster', price=2890, setup=8900, tb=12, offsite=240, hours=4,   extra=60, mix=0.20),
}
for t in tiers.values():
    t['hw'] = t['nodes'] * node_cost(t['size']) + sum(SHARED[t['box']].values())

LIC_NODE = 30     # Proxmox VE Basic, EUR 370 per socket per year
TB = 15           # off-site storage cost per TB per month (only for customers who take the add-on)
OTHER = 40        # 4G data plan, spare-pool share, small parts
ADDON_ARPA, ADDON_COST = 120, 0.35   # private AI box, extra storage: average per customer
OFFSITE_UPTAKE = 0.6                 # share of customers who add the off-site backup copy
LEASE36 = 0.0300  # monthly lease factor, 36 months at ~5% p.a.
SETUP_MATERIAL = 900

def direct_cost(t): return t['nodes'] * LIC_NODE + OFFSITE_UPTAKE * t['tb'] * TB + OTHER + t['extra'] + ADDON_ARPA * ADDON_COST

# ---- Financing options (shares of new customers) ----
# own:      we buy the hardware and rent it inside the monthly fee
# prepay:   like own, but the customer pays each year in advance with a 4% discount
# lease:    the customer leases the hardware directly from a leasing firm (vendor programme);
#           the lessor pays us the hardware at installation, the customer pays the lessor,
#           and our monthly fee drops by the lease instalment (customer total unchanged)
# purchase: the customer buys the hardware (cost + 15%) and pays a service-only fee
SCENARIOS = {
    'A. Self-funded, monthly': dict(own=1.0),
    'B. All leased directly by customers': dict(lease=1.0),
    'C. Recommended mix': dict(lease=0.40, prepay=0.30, purchase=0.15, own=0.15),
}
PREPAY_DISCOUNT = 0.04
PURCHASE_MARKUP = 0.15

new = [10, 21, 32, 44, 55]
churn_m = 0.03 / 12
founders = [90_000, 110_000, 150_000, 170_000, 180_000]
employees = [0, 1, 3, 5, 7]
EMP_COST = 150_000
other_opex = [90_000, 150_000, 200_000, 250_000, 300_000]

def monthly_in(t, mode):
    """Monthly cash we receive from one customer, and hardware cash at installation."""
    base = t['price'] + ADDON_ARPA + OFFSITE_UPTAKE * t['offsite']
    if mode == 'lease':
        return base - t['hw'] * LEASE36, t['hw']          # lessor pays us the hardware
    if mode == 'purchase':
        return base - t['hw'] / 36, t['hw'] * (1 + PURCHASE_MARKUP)
    if mode == 'prepay':
        return base * (1 - PREPAY_DISCOUNT), 0
    return base, 0

def run(scn, verbose=False):
    cohorts = []  # (month joined, count, tier, mode)
    cash = 0.0; low = 0.0; out = []
    for y in range(5):
        rev = ebitda = 0.0
        opex = 2 * founders[y] + employees[y] * EMP_COST + other_opex[y]
        for m in range(12):
            month = y * 12 + m
            n_new = new[y] / 12
            for tname, t in tiers.items():
                for mode, share in scn.items():
                    cohorts.append((month, n_new * t['mix'] * share, t, mode))
            flow = -opex / 12
            for (j, n, t, mode) in cohorts:
                alive = n * (1 - churn_m) ** (month - j)
                fee, hw_in = monthly_in(t, mode)
                if mode == 'prepay':
                    fee_now = fee * 12 if (month - j) % 12 == 0 else 0
                else:
                    fee_now = fee
                flow += alive * (fee_now - direct_cost(t))
                if month == j:  # installation month
                    flow += n * (t['setup'] - SETUP_MATERIAL + hw_in)
                    flow -= n * t['hw']                     # we always buy the box first
                rev += alive * fee_now + (n * (t['setup'] + hw_in) if month == j else 0)
            cash += flow; low = min(low, cash); ebitda += flow
        cust = sum(n * (1 - churn_m) ** (59 - j) for (j, n, t, mode) in cohorts if j <= y * 12 + 11)
        out.append((2027 + y, cust, rev, cash))
    return low, out

if __name__ == '__main__':
    print('Hardware per box (CHF):')
    for name, t in tiers.items():
        print(f"  {name:9s} {t['nodes']} node(s), node {node_cost(t['size']):,} + shared {sum(SHARED[t['box']].values()):,} = {t['hw']:,}"
              f"  -> lease {t['hw']*LEASE36:,.0f}/month over 36 months")
    print('\nMonthly contribution after direct costs and staff time (CHF 110/h), and hardware payback (own financing):')
    for name, t in tiers.items():
        rev = t['price'] + ADDON_ARPA + OFFSITE_UPTAKE * t['offsite']
        contrib = rev - direct_cost(t) - t['hours'] * 110
        print(f"  {name:9s} price {t['price']:,} + avg add-ons {rev - t['price']:,.0f} | direct {direct_cost(t):,.0f} | staff {t['hours']}h"
              f" -> contribution {contrib:,.0f}/month ({contrib/rev:.0%}) -> payback {t['hw']/contrib:4.1f} months")
    arpa = sum(t['price'] * t['mix'] for t in tiers.values())
    addons = ADDON_ARPA + sum(OFFSITE_UPTAKE * t['offsite'] * t['mix'] for t in tiers.values())
    print(f"\nBlended list price per customer: CHF {arpa:,.0f}/month (+ CHF {addons:,.0f} average add-ons)")
    print('\nCash by scenario (cash flow incl. hardware purchases, CHF thousands):')
    for name, scn in SCENARIOS.items():
        low, rows = run(scn)
        line = '  '.join(f"{y}: {c/1e3:6.0f}" for (y, cust, rev, c) in rows)
        print(f"  {name:38s} peak need {-low/1e3:5.0f}k | year-end cash {line}")
