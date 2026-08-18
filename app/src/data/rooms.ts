export interface Room {
  id: string
  title: string
  client: string
  img: string
  tagline: string
  description: string[]
  features: string[]
  price: string
  priceNote: string
  sqm: string
  occupancy: string
  bed: string
}

export const rooms: Room[] = [
  {
    id: '01',
    title: 'Ocean Suite',
    client: 'Marine Wing',
    img: 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=1600&h=900&fit=crop&q=80',
    tagline: 'A quiet room opening directly onto the tide.',
    description: [
      'A corner suite in the Marine Wing, the Ocean Suite was designed around a single gesture: a seven-metre wall of glass that slides away entirely. The sea enters the room. The room steps out onto the balcony.',
      'Interiors are kept soft — limewashed walls, oak floors, linen drapery in natural bone. The bathroom is carved from a single block of travertine, with a deep soaking tub set beside a north-facing window.',
    ],
    features: [
      'Floor-to-ceiling retractable glass facade',
      'Private sea-view balcony, 14m²',
      'Travertine soaking tub with ocean view',
      'King bed with hand-spun linen sheets',
      'Byredo amenities and Japanese tea bar',
      'Daily turndown, twice-daily housekeeping',
    ],
    price: '$680',
    priceNote: 'per night, taxes included',
    sqm: '55m²',
    occupancy: '2 guests',
    bed: 'King bed',
  },
  {
    id: '02',
    title: 'Private Villa',
    client: 'Coral Residences',
    img: 'https://images.unsplash.com/photo-1540541338287-41700207dee6?w=1600&h=900&fit=crop&q=80',
    tagline: 'Two-bedroom villa with a private plunge pool.',
    description: [
      'Set behind a low stone wall a few steps from the shoreline, this standalone villa is the most secluded address on the property. A private path leads through a garden of olive and fig to a covered terrace, plunge pool, and sunken lounge.',
      'Inside, two bedrooms flank a generous open-plan living space with a wood-burning fireplace. The kitchenette is fully equipped; a resident butler prepares breakfast on the terrace each morning.',
    ],
    features: [
      'Two king bedrooms, two bathrooms',
      'Private 10m heated plunge pool',
      'Outdoor terrace with covered dining for 8',
      'Resident butler service (6am – 11pm)',
      'Wood-burning fireplace and wine cellar',
      'Direct beach path, 90 seconds on foot',
    ],
    price: '$2,400',
    priceNote: 'per night, minimum two-night stay',
    sqm: '180m²',
    occupancy: '4 guests',
    bed: '2 king beds',
  },
  {
    id: '03',
    title: 'Horizon Loft',
    client: 'Sky Terrace',
    img: 'https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=1600&h=900&fit=crop&q=80',
    tagline: 'A double-height room at the top of the cliff.',
    description: [
      'Occupying the entire top floor of the Sky Terrace wing, the Horizon Loft is built on a single principle: unobstructed sky. The ceiling rises to five metres; the south-facing wall is glass from floor to rafter.',
      'A mezzanine library overlooks the main living space, with a reading chair tucked beside the west window for late-afternoon light. The bedroom is on the lower level, opening to a quiet garden courtyard.',
    ],
    features: [
      'Double-height living space, 5m ceilings',
      'Mezzanine library with curated reading',
      'Panoramic 180° ocean view',
      'King bed in ground-level garden wing',
      'Rainfall shower and deep soaking tub',
      'In-room Bang & Olufsen speakers',
    ],
    price: '$920',
    priceNote: 'per night, breakfast included',
    sqm: '70m²',
    occupancy: '2 guests',
    bed: 'King bed',
  },
  {
    id: '04',
    title: 'Beachfront Studio',
    client: 'Tide Pavilion',
    img: 'https://images.unsplash.com/photo-1582719508461-905c673771fd?w=1600&h=900&fit=crop&q=80',
    tagline: 'An open-plan studio steps from the sand.',
    description: [
      'The Tide Pavilion is a row of six low, gabled studios running parallel to the beach. Each is a single, uncluttered room — a bed, a writing desk, a soft reading chair beside the window.',
      'A wide sliding door opens onto a private deck with direct sand access. No balconies, no corridors, no one overhead. A short flight of wooden steps takes you down to the water.',
    ],
    features: [
      'Direct beach access, no stairs to sand',
      'Private wooden deck with lounger',
      'Open-plan studio layout, 40m²',
      'Queen bed with natural linen',
      'Outdoor shower garden',
      'Morning coffee tray on the deck',
    ],
    price: '$540',
    priceNote: 'per night, two-person occupancy',
    sqm: '40m²',
    occupancy: '2 guests',
    bed: 'Queen bed',
  },
  {
    id: '05',
    title: 'Cliffside Suite',
    client: 'Cove Residence',
    img: 'https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=1600&h=900&fit=crop&q=80',
    tagline: 'A suite cut into the cliff face, with an outdoor tub.',
    description: [
      'The Cliffside Suite sits at the north edge of the property, where the land drops forty metres straight to the sea. The suite is partially built into the rock: one wall is native stone, cool and dry to the touch.',
      'A private terrace holds an outdoor copper soaking tub positioned to face the sunset. In the evening the staff light the terrace with hurricane lanterns. Dinner can be served here by request.',
    ],
    features: [
      'Outdoor copper soaking tub on private terrace',
      'Exposed natural stone feature wall',
      'West-facing terrace for sunset viewing',
      'King bed with canopy drapery',
      'Private dining service available',
      'Evening turndown with lantern lighting',
    ],
    price: '$1,150',
    priceNote: 'per night, seasonal rate',
    sqm: '85m²',
    occupancy: '2 guests',
    bed: 'King bed',
  },
  {
    id: '06',
    title: 'Seaview Villa',
    client: 'Palm Terrace',
    img: 'https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=1600&h=900&fit=crop&q=80',
    tagline: 'A three-bedroom villa with a full infinity pool.',
    description: [
      'The Palm Terrace Villa is the largest residence on the property, occupying the western headland. Three bedroom suites wrap around a central courtyard planted with olive and bougainvillaea.',
      'The signature feature is a 22-metre infinity pool running along the cliff edge, its far rim dissolving into the horizon. A private chef can be arranged for the duration of the stay; a 4-hour spa treatment is included on arrival.',
    ],
    features: [
      '22m infinity-edge pool along cliff',
      'Three king bedrooms, three full bathrooms',
      'Private chef available on request',
      'Arrival spa treatment (4 hours) included',
      'Dedicated villa manager and housekeeper',
      'Airport transfer in Villa vehicle',
    ],
    price: '$3,200',
    priceNote: 'per night, minimum three-night stay',
    sqm: '320m²',
    occupancy: '6 guests',
    bed: '3 king beds',
  },
]
