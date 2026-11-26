# Hardware, plans and financing

*As of 2026-11-26. Product name: **Rechenbox**, domain **rechenbox.ch** (still check Zefix and Swissreg for the name). Pilot region: **St. Gallen**. Replaces the "Hardware reference design" in section 2b of the plan and the pricing and unit economics in 2a. Prices are estimates in CHF excl. VAT unless a source is linked. Figures marked "lab" must be measured before they go into a sales promise.*

**Decision:** two boxes, three plans.

- **Start** is one small-form-factor node with a firewall, a UPS and a separate backup box, in a small 10-inch cabinet. If the node fails, a pre-installed replacement arrives the next working day and data comes back from the local backup.
- **Business and Pro** run on the same cluster: three small-form-factor nodes in a closed 10-inch cabinet about 50 cm high, with failover. **They differ only in support and price.**
- **Every box has a simple web portal.** Customers add staff, shares, access rights and apps themselves; the box is monitored in the background. Support plans therefore contain no "change hours", only how fast and when incidents are handled. On the website, monitoring is described as something that happens, not as us watching.
- **Local backup is included; the copy in a Swiss data centre is an optional add-on.** We recommend it, because a local backup alone does not survive a fire, theft or a ransomware attack that reaches the backup box.

| Plan | Hardware | Price/month | Setup | Hardware cost | 36-month lease |
| --- | --- | --- | --- | --- | --- |
| Start | 1 node, 64 GB, ~3 TB usable | 790 | 2,900 | ~5,600 | ~170/month |
| Business | 3 nodes, 96 GB each, ~6 TB usable | 1,890 | 6,900 | ~13,700 | ~410/month |
| Pro | Same as Business | 2,890 | 8,900 | ~13,700 | ~410/month |

Add-ons per month: off-site backup copy CHF 90 (Start), 140 (Business), 240 (Pro, 1-year retention); more storage (+6 TB usable) CHF 190; private AI CHF 590.

## 1. Support is what separates Business from Pro

| | Start | Business | Pro |
| --- | --- | --- | --- |
| If hardware fails | Replacement next working day, restore from backup | No interruption, replacement next working day | No interruption, replacement within a day, weekends included |
| Alerting for incidents | Mon–Fri, office hours | Mon–Fri, office hours | Around the clock, 7 days |
| Response to incidents | Next working day | Same working day | Same day, weekends included |
| Self-service web portal (users, shares, access, apps) | Yes | Yes | Yes |
| Monitoring around the clock (alerts handled as above) | Yes | Yes | Yes |
| Contact | Support team | Support team | Named technician |
| Monthly restore test with report | Yes | Yes | Yes |
| Local backup retention | 30 days | 90 days | 1 year |
| Second copy in a Swiss data centre | Optional | Optional | Optional |
| Disaster-recovery test with report | – | – | Yearly |
| Evidence for auditors and insurers | Monthly report | Monthly report | Monthly report, quarterly review, evidence folder |

## 1b. The self-service web portal

Customers do their own day-to-day changes in a web portal on the box. This keeps our staff time per customer low and gives customers instant changes instead of tickets. It is also a product we have to build or choose.

**MVP scope:** add and remove staff (account, MFA enrolment), groups and shared folders with access rights, password and MFA resets, a device for remote access, restore a file or folder from the backup, install an app from our tested catalogue, a status page (backups, updates, health, capacity), and a button to contact us. Guard rails: every action is logged, nobody gets root access, risky actions such as deleting a user have an undo window, and our monitoring flags configuration drift.

| Option | What it gives | Drawbacks | Verdict |
| --- | --- | --- | --- |
| [Univention Corporate Server](https://www.univention.com/products/ucs/) (Bremen) as directory and portal | Windows-compatible directory (Samba AD), web management of users, groups and shares, app centre, Keycloak for single sign-on | Admin screens are made for IT people, not office managers | **MVP base:** covers directory and portal fast |
| Our own thin portal on the APIs of the directory, Keycloak, Nextcloud, Proxmox and Backup Server | Exactly the tasks customers need, our brand, our guard rails | Engineering effort (estimate: 2–3 months for an MVP) and ongoing upkeep | **Target from 2028**, once we know which tasks customers actually use |
| Nextcloud admin plus the Proxmox interface as they are | Free, already there | Two technical interfaces, easy to break things | No |
| Cockpit or Webmin | Generic server administration | Far too technical | No |

**Staffing:** response times are deliberately within a day, not within the hour, so a small team can carry them. Pro's 24/7 alerting means alerts reach someone at any time and are handled the same day, weekends included. That needs one person on weekend call, which two founders can share in 2027; from 2028 the first engineer joins the rota.

## 2. What is in the boxes

| Unit | Start | Business / Pro |
| --- | --- | --- |
| Nodes | 1 × MS-A2-class mini PC, 64 GB, 2 × 3.84 TB PLP NVMe (ZFS mirror) | 3 × MS-A2-class, 96 GB, 2 × 3.84 TB PLP NVMe (Ceph) |
| Firewall | Fanless OPNsense appliance | Same |
| Switch | Small 2.5 GbE switch | Fanless 2.5 GbE switch with 2 × SFP+ |
| Backup | Small backup box, Proxmox Backup Server | Larger backup box, separate from the cluster |
| Remote hands | 1 IP-KVM, smart plug, 4G router | 3 IP-KVMs, switched PDU, 4G router |
| UPS | Lithium, ~700 VA | Lithium, ~1,000 VA (lasts the 5-year term) |
| Cabinet | 10-inch, 6U | 10-inch, 9U, closed, dust filter, two slow 120 mm fans |
| Hardware total | ~5,600 | ~13,700 |

**Memory is the single biggest cost.** DDR5 retail prices are about 6× their July 2025 level and still rising ([3DCenter via Guru3D](https://www.guru3d.com/story/eu-ddr5-retail-prices-climb-again-with-highcapacity-kits-near-nine-times-baseline/)). 96 GB is ~40% of a cluster node. Three levers: start at 64 GB and add memory when needed, buy in batches when prices dip, move modules into the next node generation at refresh.

## 3. How the cluster works

- **Storage:** Ceph across the three nodes keeps 3 copies, so a node can fail without data loss or a stop. Drives must be enterprise NVMe with power-loss protection (M.2 22110 or U.2); consumer SSDs make Ceph slow and unsafe. Usable: ~5.8 TB with 25% kept free for self-healing.
- **Storage network:** the two 10G SFP+ ports per node connect the nodes directly to each other (full mesh, DAC cables), so no 10G switch is needed ([Proxmox wiki](https://pve.proxmox.com/wiki/Full_Mesh_Network_for_Ceph_Server)).
- **Backup:** a separate small box runs Proxmox Backup Server. With the add-on, a server in a Swiss data centre pulls encrypted copies from it, so a compromised box cannot delete them. A backup inside the cluster would not survive a cluster-wide fault or ransomware.
- **Remote management:** mini PCs have no management controller (BMC). An IP-KVM per node gives us screen and keyboard; the switched PDU power-cycles a hung node. Both work over the 4G router when the office internet is down.

## 4. Which kind of node

| | Prosumer mini PC ([Minisforum MS-A2](https://www.servethehome.com/minisforum-ms-a2-review-an-almost-perfect-amd-ryzen-intel-10gbe-homelab-system/) class) | Business mini PC (Lenovo Tiny, HP, Dell Micro) | Compact server ([Supermicro AS-E300-14GR](https://www.supermicro.com/en/products/system/iot/fan-based%20embedded/as-e300-14gr), [ASRock Rack EPYC 4005](https://www.asrockrack.com/minisite/AMD-EPYC-4005-Server)) |
| --- | --- | --- | --- |
| CPU | Ryzen 9 9955HX, 16 cores | 6–16 cores, laptop-class | EPYC 4005, up to 16 cores, 65 W |
| 10G networking | 2 × SFP+ built in | None | 2–4 × 10G on some models |
| Drives | 3 slots, U.2 capable | 1–2 slots | 2+ slots |
| ECC memory | Partly works in tests; unverified | No | Yes |
| Remote management | None: needs IP-KVM | Intel vPro or AMD DASH | Full BMC/IPMI |
| Warranty | 1–2 years, return to base | 3–5 years on-site | 3 years |
| Barebone price | ~CHF 750–900 ([launch $839](https://store.minisforum.com/products/minisforum-ms-a2)) | ~CHF 900–1,400 | ~CHF 1,500–2,500 |

**Recommendation:** pilot with the prosumer class, the only one with built-in 10G, enough drive slots and good price per core. Test one compact server (ECC, BMC) alongside in the lab as the fallback if buyers object to a consumer brand. Our answer to that objection is the design: three copies on three nodes, a spare on its way, firmware updates rolled out by us in stages, Secure Boot and TPM-backed disk encryption.

## 5. Spares instead of warranty

A failed node is **swapped, not repaired**. A pre-installed spare goes out by courier from St. Gallen (Start, Business: next working day; Pro: within a day, weekends included). Ceph rebuilds the copies; on Start we restore from the local backup. Spare pool: one node per 15 boxes, plus one backup box and UPS per 30.

## 6. Power and noise (lab)

| | Business / Pro box | 3 × 1U servers (earlier design) |
| --- | --- | --- |
| Typical draw | ~120–180 W (design target) | ~450–600 W |
| Energy per year | ~1,300 kWh | ~4,500 kWh |
| Electricity at ~CHF 0.27/kWh | ~CHF 350/year | ~CHF 1,200/year |
| Noise at 1 m, office load | < 30 dB(A) target | 45–55 dB(A) |

Start draws roughly a third of the cluster. Measure both on the lab boxes first: "quiet enough for the reception desk" and "about CHF 30 of electricity a month" only sell once proven.

## 7. Private AI add-on

The AI runs on its **own box**, so a heavy AI job never slows the office applications. Recommended: a Ryzen AI Max+ 395 mini workstation with 128 GB of shared memory, e.g. HP Z2 Mini G1a (business warranty; [~$3,700–5,000](https://www.notebookcheck.net/Z2-Mini-G1a-HP-reveals-comparatively-high-US-pricing-among-over-a-dozen-AMD-Ryzen-AI-Max-variants.1034018.0.html) for 128 GB), about CHF 4,000–4,500. The CHF 590/month add-on pays it back in about 11 months after its running costs. It works with every plan.

## 8. Unit economics

| Plan | Price + avg. add-ons | Direct costs¹ | Staff time² | Contribution | Hardware payback (own financing) |
| --- | --- | --- | --- | --- | --- |
| Start | 964 | 139 | 1.5 h = 165 | 660 (68%) | ~8.5 months |
| Business | 2,094 | 226 | 2.5 h = 275 | 1,593 (76%) | ~8.5 months |
| Pro | 3,154 | 340 | 4 h = 440 | 2,374 (75%) | ~6 months |

Average add-ons assume 60% of customers take the off-site copy plus CHF 120 of AI and storage add-ons. ¹ Licences, off-site storage for those who take it, 4G, spares share, add-on costs; Pro also carries its share of the weekend on-call allowance. ² Following up monitoring alerts, incidents, reviews and drills, at CHF 110/h. No change hours, because customers use the portal.

The portal is what makes these margins possible: without it, every new employee or access change becomes a ticket. Its build cost sits in the engineering headcount, not in the unit economics.

## 9. Offsetting the hardware cost

1. **Customers lease directly from a leasing firm (vendor programme).** The lessor pays us for the box at installation and carries the credit risk; the customer pays the lessor, and our monthly fee drops by the instalment, so the customer's total stays the same. Leasing to a young company ourselves is much harder to get.
2. **Pay a year in advance with 4% off.** A Start customer then pays about CHF 11,100 up front, twice what the box costs; a Business customer about CHF 24,100 against CHF 13,700.
3. **Purchase option.** The customer buys the hardware (cost plus 15%) and pays a service-only fee (Start: about CHF 810 instead of CHF 960 including the average add-ons). It ties up no capital of ours, but weakens lock-in and puts the refresh decision back with the customer.
4. **The fee keeps its hardware share after month 36.** The box is paid off but runs to month 60; years 4–5 fund the next refresh.
5. **Second life.** Refreshed nodes become off-site backup nodes, lab and spare units, or are sold refurbished. Memory moves into the next generation if the slot type still fits.
6. **Supplier terms and setup fee.** Distributor terms of 30–60 days plus the setup fee due at installation cover part of each box before its invoice is due.

| Financing scenario (`python3 docs/model.py`) | Peak capital need | Cash end of 2031 |
| --- | --- | --- |
| A. We buy and rent all hardware | ~CHF 730k | ~CHF −60k |
| B. All customers lease directly | ~CHF 310k | ~CHF 560k |
| C. **Recommended:** 40% direct lease, 30% prepay, 15% purchase, 15% own | ~CHF 290k | ~CHF 740k |

## 10. What the new plans do to the business plan

The cheaper Start plan lowers the blended price per customer from about CHF 1,890 to CHF 1,650 a month (before add-ons). At the same customer numbers, peak capital need rises from about CHF 210k to **about CHF 290k**, and cash breaks even at the end of 2030. Volume matters more than price:

| Variant (recommended financing mix) | Peak capital need | Cash end of 2031 |
| --- | --- | --- |
| Base: 790 / 1,890 / 2,890, mix 40 / 40 / 20 | ~CHF 290k | ~CHF 740k |
| Start at CHF 990 | ~CHF 240k | ~CHF 1.0M |
| More Business and Pro (mix 30 / 45 / 25) | ~CHF 195k | ~CHF 1.3M |
| 20% more customers, because Start lowers the entry barrier | ~CHF 155k | ~CHF 1.8M |
| Start at CHF 990 and 20% more customers | ~CHF 135k | ~CHF 2.2M |
| Only 30% take the off-site copy | ~CHF 300k | ~CHF 675k |

The engagement test answers this: the website records which plan the recommender suggests, which plan people reserve, how they rate the price and how they want to pay. If Start draws many more sign-ups than the old CHF 1,190 entry would have, the cheaper entry pays for itself; if most people land on Start and few on Business, raise Start to CHF 890–990.

**For the plan doc** (this session can no longer edit it): replace the pricing table and unit economics in 2a with sections 1 and 8 here, the hardware table in 2b with section 2, add the portal (section 1b) to the 2b service stack, add the spare-node model to Operations, change the region from Zurich to St. Gallen, and set the funding ask to about CHF 300k until the test shows the volume effect.

## 11. Lab test before the first pilot

- [ ] Build one Start box and one cluster box. Measure power at idle, office load and full load, and noise at 1 m with the cabinet closed
- [ ] Ceph on three nodes with full-mesh 10G: latency and throughput with PLP drives; pull a node during a file copy
- [ ] Start box: time a full restore of all VMs from the backup box onto a replacement node
- [ ] Check ECC on the MS-A2 with the chosen memory kit; check BIOS updates and Secure Boot
- [ ] Time a node swap by a non-expert following written instructions
- [ ] Compare one compact server (EPYC 4005, BMC) on the same tests
- [ ] Ask 2 leasing firms for vendor-programme terms on a CHF 5.6k and a CHF 13.7k box over 36 months
- [ ] Get a quote from a partner NOC for night and weekend incident cover (Pro)
- [ ] Portal: let a non-technical office manager do 5 everyday tasks in Univention's web interface, and note where they get stuck
