import { useEffect, useState } from 'react'
import { rooms } from '../data/rooms'
import { trpc } from '@/providers/trpc'
import { useAuth } from '@/hooks/useAuth'

interface RoomDetailProps {
  roomId: string
  onBack: () => void
}

function getOAuthUrl() {
  const kimiAuthUrl = import.meta.env.VITE_KIMI_AUTH_URL
  const appID = import.meta.env.VITE_APP_ID
  const redirectUri = `${window.location.origin}/api/oauth/callback`
  const state = btoa(redirectUri)

  const url = new URL(`${kimiAuthUrl}/api/oauth/authorize`)
  url.searchParams.set('client_id', appID)
  url.searchParams.set('redirect_uri', redirectUri)
  url.searchParams.set('response_type', 'code')
  url.searchParams.set('scope', 'profile')
  url.searchParams.set('state', state)

  return url.toString()
}

export default function RoomDetail({ roomId, onBack }: RoomDetailProps) {
  const room = rooms.find((r) => r.id === roomId)
  const [hovered, setHovered] = useState(false)
  const [reserveStatus, setReserveStatus] = useState<'idle' | 'reserved'>('idle')
  const { user, isLoading: authLoading } = useAuth()

  const createReservation = trpc.reservation.create.useMutation({
    onSuccess: () => {
      setReserveStatus('reserved')
    },
  })

  const handleReserve = () => {
    if (!room) return
    if (!user) {
      // Store intended reservation in sessionStorage, redirect to login
      sessionStorage.setItem('pending_reservation_room_id', room.id)
      sessionStorage.setItem('pending_reservation_room_title', room.title)
      window.location.href = getOAuthUrl()
      return
    }
    createReservation.mutate({
      checkInDate: '',
      checkOutDate: '',
      guests: '2',
      roomType: room.title,
      roomId: room.id,
      fullName: user.name || '',
      email: user.email || '',
    })
  }

  // Check for pending reservation after OAuth redirect
  useEffect(() => {
    const pendingRoomId = sessionStorage.getItem('pending_reservation_room_id')
    const pendingRoomTitle = sessionStorage.getItem('pending_reservation_room_title')
    if (pendingRoomId && pendingRoomTitle && user && roomId === pendingRoomId) {
      sessionStorage.removeItem('pending_reservation_room_id')
      sessionStorage.removeItem('pending_reservation_room_title')
      createReservation.mutate({
        checkInDate: '',
        checkOutDate: '',
        guests: '2',
        roomType: pendingRoomTitle,
        roomId: pendingRoomId,
        fullName: user.name || '',
        email: user.email || '',
      })
    }
  }, [user, roomId])

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' })
  }, [roomId])

  if (!room) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#ffffff',
          color: '#000000',
          flexDirection: 'column',
          gap: '20px',
        }}
      >
        <p style={{ fontSize: '20px' }}>Room not found.</p>
        <button
          onClick={onBack}
          style={{
            fontSize: '13px',
            letterSpacing: '0.14em',
            padding: '14px 32px',
            border: '1px solid #000',
            backgroundColor: 'transparent',
            cursor: 'pointer',
            textTransform: 'uppercase',
          }}
        >
          ← Back to rooms
        </button>
      </div>
    )
  }

  return (
    <div style={{ backgroundColor: '#ffffff', minHeight: '100vh' }}>
      {/* Hero image */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: 'clamp(400px, 70vh, 720px)',
          overflow: 'hidden',
          backgroundColor: '#0b0b0b',
        }}
      >
        <img
          src={room.img}
          alt={room.title}
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
        />
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background:
              'linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0) 40%, rgba(0,0,0,0.55) 100%)',
          }}
        />
        <button
          onClick={onBack}
          style={{
            position: 'absolute',
            top: 'clamp(100px, 14vh, 140px)',
            left: 'clamp(24px, 4vw, 60px)',
            fontSize: '12px',
            letterSpacing: '0.16em',
            padding: '12px 24px',
            border: '1px solid #ffffff',
            backgroundColor: 'rgba(0,0,0,0.35)',
            color: '#ffffff',
            cursor: 'pointer',
            textTransform: 'uppercase',
            fontFamily: '"Helvetica Neue", sans-serif',
            backdropFilter: 'blur(6px)',
            WebkitBackdropFilter: 'blur(6px)',
          }}
        >
          ← Back
        </button>
        <div
          style={{
            position: 'absolute',
            bottom: 'clamp(32px, 5vw, 60px)',
            left: 'clamp(24px, 4vw, 60px)',
            right: 'clamp(24px, 4vw, 60px)',
            color: '#ffffff',
          }}
        >
          <p
            style={{
              fontSize: '12px',
              letterSpacing: '0.2em',
              textTransform: 'uppercase',
              opacity: 0.8,
              marginBottom: '12px',
            }}
          >
            Room {room.id} · {room.client}
          </p>
          <h1
            style={{
              fontSize: 'clamp(36px, 6vw, 80px)',
              fontWeight: 400,
              letterSpacing: '-0.03em',
              lineHeight: 1.02,
              margin: 0,
              maxWidth: '900px',
            }}
          >
            {room.title}
          </h1>
        </div>
      </div>

      {/* Body */}
      <div
        style={{
          maxWidth: '1400px',
          margin: '0 auto',
          padding: '80px clamp(24px, 4vw, 60px) 120px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))',
          gap: 'clamp(40px, 5vw, 80px)',
          alignItems: 'flex-start',
        }}
      >
        {/* Left: description + features */}
        <div style={{ flex: '2 1 600px', minWidth: 0 }}>
          <p
            style={{
              fontSize: 'clamp(20px, 2.2vw, 30px)',
              fontWeight: 400,
              lineHeight: 1.4,
              letterSpacing: '-0.015em',
              color: '#000000',
              marginBottom: '48px',
              maxWidth: '680px',
            }}
          >
            {room.tagline}
          </p>

          {room.description.map((p, i) => (
            <p
              key={i}
              style={{
                fontSize: '16px',
                lineHeight: 1.8,
                color: '#333333',
                marginBottom: '24px',
                maxWidth: '680px',
              }}
            >
              {p}
            </p>
          ))}

          <div
            style={{
              marginTop: '64px',
              paddingTop: '32px',
              borderTop: '1px solid #1a1a1a',
            }}
          >
            <p
              style={{
                fontSize: '11px',
                letterSpacing: '0.22em',
                color: '#000000',
                textTransform: 'uppercase',
                marginBottom: '28px',
              }}
            >
              Room Features
            </p>
            <ul
              style={{
                listStyle: 'none',
                padding: 0,
                margin: 0,
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))',
                gap: '14px 40px',
              }}
            >
              {room.features.map((f) => (
                <li
                  key={f}
                  style={{
                    fontSize: '15px',
                    lineHeight: 1.6,
                    color: '#333333',
                    paddingLeft: '20px',
                    position: 'relative',
                  }}
                >
                  <span
                    style={{
                      position: 'absolute',
                      left: 0,
                      top: '12px',
                      width: '8px',
                      height: '1px',
                      backgroundColor: '#000000',
                    }}
                  />
                  {f}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Right: booking panel */}
        <aside
          style={{
            flex: '1 1 320px',
            minWidth: 0,
            position: 'sticky',
            top: '112px',
            border: '1px solid #000000',
            padding: '32px 28px',
            backgroundColor: '#ffffff',
          }}
        >
          <p
            style={{
              fontSize: '11px',
              letterSpacing: '0.22em',
              textTransform: 'uppercase',
              color: '#666666',
              marginBottom: '12px',
            }}
          >
            From
          </p>
          <p
            style={{
              fontSize: 'clamp(36px, 4vw, 52px)',
              fontWeight: 400,
              letterSpacing: '-0.03em',
              lineHeight: 1,
              color: '#000000',
              marginBottom: '6px',
            }}
          >
            {room.price}
          </p>
          <p
            style={{
              fontSize: '13px',
              color: '#666666',
              lineHeight: 1.5,
              marginBottom: '28px',
            }}
          >
            {room.priceNote}
          </p>

          <dl
            style={{
              borderTop: '1px solid #e5e5e5',
              borderBottom: '1px solid #e5e5e5',
              padding: '16px 0',
              margin: '0 0 28px',
              display: 'grid',
              gap: '10px',
            }}
          >
            <Row k="Size" v={room.sqm} />
            <Row k="Occupancy" v={room.occupancy} />
            <Row k="Bed" v={room.bed} />
          </dl>

          {reserveStatus === 'reserved' ? (
            <div
              style={{
                width: '100%',
                padding: '16px 24px',
                fontSize: '13px',
                lineHeight: 1.6,
                color: '#1a6b3a',
                backgroundColor: '#e8f5e9',
                border: '1px solid #1a6b3a',
                textAlign: 'center',
              }}
            >
              Reservation submitted. Our team will contact you shortly.
            </div>
          ) : (
            <button
              onClick={handleReserve}
              disabled={createReservation.isPending || authLoading}
              onMouseEnter={() => setHovered(true)}
              onMouseLeave={() => setHovered(false)}
              style={{
                width: '100%',
                fontSize: '13px',
                fontWeight: 500,
                letterSpacing: '0.16em',
                color: hovered ? '#ffffff' : '#000000',
                backgroundColor: hovered ? '#000000' : '#ffffff',
                border: '1px solid #000000',
                padding: '16px 24px',
                cursor: (createReservation.isPending || authLoading) ? 'wait' : 'pointer',
                textTransform: 'uppercase',
                transition: 'all 0.25s ease',
                fontFamily: '"Helvetica Neue", sans-serif',
                opacity: (createReservation.isPending || authLoading) ? 0.6 : 1,
              }}
            >
              {createReservation.isPending ? 'Submitting...' : 'Reserve This Room'}
            </button>
          )}
          <button
            onClick={onBack}
            style={{
              width: '100%',
              marginTop: '14px',
              fontSize: '12px',
              letterSpacing: '0.14em',
              color: '#666666',
              backgroundColor: 'transparent',
              border: 'none',
              padding: '10px',
              cursor: 'pointer',
              textTransform: 'uppercase',
              fontFamily: '"Helvetica Neue", sans-serif',
            }}
          >
            ← Back to rooms
          </button>
        </aside>
      </div>
    </div>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '13px',
        color: '#333333',
      }}
    >
      <dt style={{ color: '#666666' }}>{k}</dt>
      <dd style={{ margin: 0, fontWeight: 500, color: '#000000' }}>{v}</dd>
    </div>
  )
}
