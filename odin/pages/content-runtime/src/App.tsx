import React, { useState, useEffect, useRef } from 'react';
import { useStorage } from '@extension/shared';
import { 
  createClick, 
  fetchClick, 
  fetchClickItems,
  createChat,
} from '@extension/shared/lib/hooks/api';
import { type Click, type Item } from '@extension/shared/lib/hooks/types';
import { profileStorage } from '@extension/storage';
import { Box } from '@mui/material';
import { v4 as uuid } from 'uuid';

interface Coordinates {
  x: number;
  y: number;
  pageX: number;
  pageY: number;
  element?: string;
}

interface ModalProps {
  screenshot: string;
  coordinates: Coordinates | null;
  boxTopLeft: Coordinates | null;
  boxBottomRight: Coordinates | null;
  isBoxComplete: boolean;
  onClose: () => void;
  style: React.CSSProperties;
}

const Modal: React.FC<ModalProps> = ({ 
  screenshot, 
  coordinates, 
  boxTopLeft,
  boxBottomRight,
  isBoxComplete,
  onClose, 
  style, 
}) => {
  const profile = useStorage(profileStorage);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [click, setClick] = useState<Click & { items?: Item[] }>();
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [click?.masked_url, click?.items, loading]);

  useEffect(() => {
    if (!profile.id) {
      profileStorage.setId(uuid());
    }
  }, [profile]);

  /**
   * Poll for items for a click
   * @param click_id 
   */
  const pollForItems = async (click_id: string) => {
    for (const _ of [...Array(600)]) {
      await new Promise(res => setTimeout(res, 1000));
      try {
        const found = await fetchClick(click_id);
        if (found.is_processed) {
          setClick(found);
          const items = await fetchClickItems(click_id);
          setClick({ ...found, items });
          break;
        }
      } catch (err) {
        console.error(err);
      }
    }
  }

  /**
   * Get the dimensions of an image
   * @param base64 
   * @returns 
   */
  const getImageDimensions = (base64: string): Promise<{ width: number; height: number; }> => {
    return new Promise((resolve) => {
      const img = new Image();
      img.src = base64;
      img.onload = () => resolve({ width: img.width, height: img.height });
    });
  };

  useEffect(() => {
    if (!coordinates && !isBoxComplete) return;
    (async () => {
      try {
        setLoading(true);
        setError(undefined);
        const dimensions = await getImageDimensions(screenshot);
        const scaleX = dimensions.width / window.innerWidth;
        const scaleY = dimensions.height / window.innerHeight;
        const added = await createClick({
          user_id: profile.id,
          base64_image: screenshot.replace("data:image/png;base64,", ""),
          click: coordinates ? [
            Math.round(coordinates.x * scaleX),
            Math.round(coordinates.y * scaleY),
          ] : undefined,
          selection: boxTopLeft && boxBottomRight && isBoxComplete ? [
            Math.round(boxTopLeft.x * scaleX),
            Math.round(boxTopLeft.y * scaleY),
            Math.round(boxBottomRight.x * scaleX),
            Math.round(boxBottomRight.y * scaleY),
          ] : undefined,
          channel: window.location.hostname,
        });
        setClick(added);
        await pollForItems(added.click_id);
      } catch (err) {
        setError(JSON.stringify(error));
      } finally {
        setLoading(false);
      }
    })();
  }, [
    screenshot, 
    coordinates?.x, 
    coordinates?.y,
    isBoxComplete,
    error, 
    profile.id,
    boxBottomRight,
    boxTopLeft,
    coordinates,
  ]);

  const containerStyle = style;

  function CloseButton() {
    return (
      <button 
        style={{
          background: 'none',
          border: 'none',
          padding: 0,
          cursor: 'pointer',
          outline: 'none',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '50px',
          height: '50px',
        }}
        onClick={onClose}
      >
        <img 
          style={{ width: '25px' }}
          src={chrome.runtime.getURL("content-runtime/x.svg")} 
          alt="close" 
        />
      </button>
    );
  }

  function Container({ children }: { children: React.ReactNode }) {
    return (
      <div style={containerStyle}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            color: 'black',
            padding: '8px 16px',
            position: 'sticky',
            top: 0,
            backgroundColor: 'white',  // Add background color to prevent content showing through
            zIndex: 1,                // Ensure it stays above other content
            borderBottom: '1px solid rgba(0, 0, 0, 0.1)',  // Optional: add border for visual separation
          }}
        >
          <div style={{ display: 'flex' }}>
            <img 
              src={chrome.runtime.getURL('content-runtime/logo.svg')} 
              alt="logo" 
              style={{ width: '45px', height: '45px' }} 
            />
            <img 
              src={chrome.runtime.getURL('content-runtime/seeclickbuy.svg')} 
              alt="logo long" 
            />
          </div>
          <CloseButton />
        </div>
        <div>
          {children}
        </div>
      </div>
    )
  }

  const Loading = () => {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <img 
          alt="loading" 
          src={chrome.runtime.getURL("content-runtime/fetching.gif")} 
          style={{ width: '300px' }}
        />
      </div>
    );
  }

  if (!screenshot) {
    return (
      <div style={containerStyle}>
        No screenshot
      </div>
    );
  }


  const ChatBox = ({ disabled }: { disabled?: boolean }) => {
    const [text, setText] = useState<string>("");
    return (
      <div 
        style={{
          position: 'sticky',
          bottom: 0,
          backgroundColor: 'white',
          padding: '24px',
          borderTop: '1px solid rgba(0, 0, 0, 0.1)',
          height: '125px',
        }}
      >
        <div 
          style={{ 
            fontSize: '16px', 
            fontWeight: 600, 
            marginBottom: '12px',
            marginTop: '-8px',
          }}
        >
          Edit results with AI...
        </div>
        <textarea
          disabled={disabled}
          placeholder="What would you like to change?"
          rows={5}
          value={text}
          onChange={e => setText(e.target.value)}
          style={{
            color: 'black',
            width: '100%',
            borderRadius: '4px',
            resize: 'none',
            padding: '8px 12px',
            boxSizing: 'border-box',
            backgroundColor: 'white',
          }}
          onKeyDown={(e) => {
            // Prevent the event from propagating to the parent page
            e.stopPropagation();
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              if (!click) return;
              if (text.length > 0) {
                setLoading(true);
                const body = {
                  click_id: click.click_id, 
                  text: text,
                };
                createChat(body)
                .then(([click, _]) => {
                  return pollForItems(click.click_id);
                })
                .finally(() => setLoading(false));
              }
            }
          }}
        />
      </div>
    );
  };

  if (loading) {
    return (
      <Container>
        <div 
          style={{
            display: 'flex',
            flexDirection: 'column',
            height: 'calc(100vh-100px)',
            boxShadow: '0px 4px 10px rgba(0, 0, 0, 0.2)',
          }}
        >
          <div 
            style={{
              flex: 1,
              overflowY: 'auto',
              paddingBottom: '16px',
              gap: '16px',
            }}
          >
            <Loading />
          </div>
          {/* <ChatBox disabled /> */}
        </div>
      </Container>
    )
  }

  if (error) {
    return (
      <Container>
        <Box>Error: {error}</Box>
      </Container>
    )
  }

  if (click) {
    const screenRatio = click.image_size
      ? click.image_size[1] / click.image_size[0]
      : 1;
    const maskRatio = click.masked_size 
      ? click.masked_size[0] / click.masked_size[1] 
      : 1;

    const Screenshot = () => {
      return (
        <div 
          style={{
            display: 'flex',
            flexDirection: 'column',
            color: 'black',
            marginTop: '16px', 
            marginBottom: '16px', 
            marginLeft: "24px", 
            marginRight: "24px",
          }}
        >
          <div 
            style={{ 
              backgroundColor: '#F3E8FF',  // Light lilac color
              padding: '12px 16px',
              borderRadius: '12px',
              width: 'fit-content',
              marginBottom: '12px',
              fontSize: '14px',
            }}
          >
            You screenshotted...
          </div>
          <img 
            src={screenshot} 
            alt="cropped click screenshot" 
            style={{
              flexShrink: 0,
              width: `${350}px`,
              height: `${screenRatio * 350}px`,
              objectFit: 'cover',
              borderRadius: '10px',
              marginLeft: '4px'  // Small indent to align with bubble
            }} 
          />
        </div>
      )
    };
    
    const Results = ({ items }: { items: Item[] }) => {
      let message: string;
      if (!items.length) {
        message = `No results found. Please try again.`
      } else {
        message = `${items.length} shopping result${items.length === 1 ? '' : 's'}`
      }
      return (
        <div 
          style={{
            display: 'flex',
            flexDirection: 'column',
            color: 'black',
            marginTop: '16px', 
            marginBottom: '16px', 
            marginLeft: "24px", 
            marginRight: "24px",
          }}
        >
          <div 
            style={{ 
              // backgroundColor: '#F3E8FF',  // Light lilac color
              // padding: '12px 16px',
              // borderRadius: '12px',
              // width: 'fit-content',
              // marginBottom: '12px',
              // fontSize: '14px',
              marginBottom: '8px',
              fontSize: '16px',
              fontWeight: 700,
            }}
          >
            {message}
          </div>
          <div 
            style={{
              display: 'flex',
              flexDirection: 'row',  
              overflowX: 'auto',
              gap: '18px',
              WebkitOverflowScrolling: 'touch', // Smooth scrolling on iOS
              msOverflowStyle: 'none',   // Hide scrollbar in IE/Edge
              scrollbarWidth: 'none',    // Hide scrollbar in Firefox
              // @ts-ignore
              '::-webkit-scrollbar': {   // Hide scrollbar in Chrome/Safari
                display: 'none'
              }
            }}
          >
            {items.map(item => <Item key={item.item_id} item={item} />)}
          </div>
        </div>
      );
    }

    const Item = ({ item }: { item: Item }) => {
      const [isHovered, setIsHovered] = useState(false);

      return (
        <a 
          href={item.link} 
          target="_blank" 
          rel="noreferrer"
          style={{
            textDecoration: 'none',
            flexShrink: 0,
            borderRadius: '6px',
            maxWidth: '150px',
            position: 'relative',
            padding: '8px',
          }}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          <div style={{ position: 'relative' }}>
            <img 
              src={item.thumbnail} 
              alt={item.title}
              style={{
                width: '150px',
                height: '200px',
                objectFit: 'contain',
                borderRadius: '10px'
              }} 
            />
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              borderRadius: '10px',
              opacity: isHovered ? 1 : 0,
              transition: 'opacity 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <svg 
                width="24" 
                height="24" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="7" y1="17" x2="17" y2="7" />
                <polyline points="7 7 17 7 17 17" />
              </svg>
            </div>
          </div>

          <div style={{ 
            fontWeight: 700,
            marginTop: '6px',
            fontSize: '14px',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            lineHeight: '1.2',
            color: 'black',
          }}>
            {item.title}
          </div>

          <div style={{ 
            marginTop: '16px', 
            display: 'flex', 
            justifyContent: 'space-between',
            alignItems: 'center',
            color: 'black',
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              alignContent: 'center',
              columnGap: '2px',
            }}>
              <img 
                src={item.source_icon} 
                alt="source icon" 
                style={{ width: '8px', height: '8px' }}
              />
              <div style={{ fontSize: "8px", color: "gray" }}>
                {item.source.split('.')[0]}
              </div>
            </div>
            <div style={{ fontSize: '14px', fontWeight: 600 }}>
              {item.price_currency}{item.price_value.toFixed(2)}
            </div>
          </div>
        </a>
      );
    };

    const MaskedImage = () => {
      console.log("maskRatio", maskRatio)
      return (
        <div 
          style={{
            display: 'flex',
            flexDirection: 'column',
            color: 'black',
            marginTop: '16px', 
            marginBottom: '16px', 
            marginLeft: "24px", 
            marginRight: "24px",
          }}
        >
          <div 
            style={{ 
              // backgroundColor: '#F3E8FF',  // Light lilac color
              // padding: '12px 16px',
              // borderRadius: '12px',
              // width: 'fit-content',
              // marginBottom: '12px',
              // fontSize: '14px',
              marginBottom: '8px',
              fontSize: '16px',
              fontWeight: 700,
            }}
          >
            You clicked on...
          </div>
          {maskRatio < 1 ? (
            <img 
              src={click.masked_url} 
              alt="cropped mask" 
              style={{
                flexShrink: 0,
                width: "150px",
                height: `${maskRatio * 150}px`,
                objectFit: 'cover',
                borderRadius: '10px',
                marginLeft: '4px'  // Small indent to align with bubble
              }} 
            />
          ) : (
            <img 
              src={click.masked_url} 
              alt="cropped mask" 
              style={{
                flexShrink: 0,
                width: `${150 / maskRatio}px`,
                height:  "150px",
                objectFit: 'cover',
                borderRadius: '10px',
                marginLeft: '4px'  // Small indent to align with bubble
              }} 
            />
          )}
        </div>
      );
    }

    const ImageDescription = () => {
      return (
        <div 
          style={{
            display: 'flex',
            flexDirection: 'column',
            color: 'black',
            marginTop: '16px', 
            marginBottom: '16px', 
            marginLeft: "24px", 
            marginRight: "24px",
          }}
        >
          <div 
            style={{ 
              marginBottom: '8px',
              fontSize: '16px',
              fontWeight: 700,
            }}
          >
            What is it? 
          </div>
          <div style={{ fontSize: '16px' }}>
            {click.description}
          </div>
        </div>
      );
    }

    return (
      <Container>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          height: 'calc(100vh-100px)',
        }}>
          <div 
            ref={scrollContainerRef}
            style={{
              flex: 1,
              overflowY: 'auto',
              paddingBottom: '16px',
              gap: '16px',
            }}
          >
            {/* <Screenshot /> */}
            <div style={{ display: 'flex', gap: '16px' }}>
              <div style={{ flex: 1 }}>
                {click.masked_url && <MaskedImage />}
              </div>
              <div style={{ flex: 1 }}>
                {click.description && <ImageDescription />}
              </div>
            </div>
            {click.items ? <Results items={click.items ?? []}/> : null}
            {loading && <Loading />}
          </div>
          <ChatBox disabled={loading || !click.masked_url} />
        </div>
      </Container>
    )
  }

  return (
    <Container>
      <div 
        style={{
          display: 'flex',
          flexDirection: 'column',
          height: 'calc(100vh-100px)',
        }}
      >
        <div 
          style={{
            flex: 1,
            overflowY: 'auto',
            paddingBottom: '16px',
            gap: '16px',
          }}
        >
          <Loading />
        </div>
        <ChatBox disabled />
      </div>
    </Container>
  );
}

const App: React.FC = () => {
  // Stores the click coordinates
  const [coordinates, setCoordinates] = useState<Coordinates | null>(null);
  // Stores the box top left coordinate
  const [boxTopLeft, setBoxTopLeft] = useState<Coordinates | null>(null);
  // Stores the box bottom right coordinate
  const [boxBottomRight, setBoxBottomRight] = useState<Coordinates | null>(null);
  // Stores if the box is done 
  const [isBoxComplete, setIsBoxComplete] = useState<boolean>(false);
  // Stores if we are in `click` mode or `select` mode
  const [mode, setMode] = useState<'click' | 'select'>('click');
  // Stores an overlay over the existing page
  const [showOverlay, setShowOverlay] = useState<boolean>(true);
  // Stores an overlay over the box
  const [showBox, setShowBox] = useState<boolean>(false);
  // Stores the screenshot of the current page
  const [screenshot, setScreenshot] = useState<string>();

  /**
   * Listen for messages from the background script
   */
  useEffect(() => {
    const messageListener = (
      message: { type: string; payload: string },
      sender: chrome.runtime.MessageSender,
      sendResponse: (response?: unknown) => void
    ) => {
      if (message.type === 'SET_SCREENSHOT') {
        setScreenshot(message.payload);
        sendResponse({ received: true });
      }
    };
    chrome.runtime.onMessage.addListener(messageListener);
    return () => chrome.runtime.onMessage.removeListener(messageListener);
  }, []);

  /**
   * Listen for shift key to toggle between `click` and `select` modes
   */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      e.stopPropagation();
      if (e.key === 'Shift') {
        console.log('shift');
        setMode('select');
        setShowBox(true);
        setIsBoxComplete(false);
      }
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      e.stopPropagation();
      if (e.key === 'Shift') {
        console.log('click');
        setMode('click');
        setShowBox(false);
        setBoxTopLeft(null);
        setBoxBottomRight(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown); 
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  /**
   * Listen for escape key to close the modal
   */
  useEffect(() => {
    const handleEscapePress = (e: KeyboardEvent) => {
      e.stopPropagation();
      if (e.key === 'Escape') {
        console.log('escape');
        handleClose();
      }
    };
    window.addEventListener('keydown', handleEscapePress);
    return () => window.removeEventListener('keydown', handleEscapePress);
  }, []);

  /**
   * Listen for mouse movement to update the box coordinates
   */
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (mode === 'select') {
        const newCoordinates = {
          x: e.clientX,
          y: e.clientY,
          pageX: e.pageX,
          pageY: e.pageY,
          element: document.elementFromPoint(e.clientX, e.clientY)?.outerHTML
        };
        setBoxBottomRight(newCoordinates);
      }
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [mode]);

  /**
   * Handle a click event
   * This handles both `click` and `select` modes
   * @param e 
   */
  const handleClick = async (e: React.MouseEvent) => {
    const newCoordinates = {
      x: e.clientX,
      y: e.clientY,
      pageX: e.pageX,
      pageY: e.pageY,
      element: document.elementFromPoint(e.clientX, e.clientY)?.outerHTML
    };
    if (mode === 'click') {
      setCoordinates(newCoordinates);
      setShowOverlay(false);
      document.body.style.overflow = '';
    } else {
      if (!boxTopLeft) {
        console.log('set top left');
        setBoxTopLeft(newCoordinates);
      // New coordinates must be to the right and down from the top left
      } else if (newCoordinates.x > boxTopLeft.x && newCoordinates.y > boxTopLeft.y) {
        console.log('set bottom right');
        setBoxBottomRight(newCoordinates);
        setShowOverlay(false);
        setShowBox(false);
        setIsBoxComplete(true);
        document.body.style.overflow = '';
      }
    }
  };

  /**
   * Handle closing the modal
   */
  const handleClose = () => {
    setCoordinates(null);
    setBoxTopLeft(null);
    setBoxBottomRight(null);
    setIsBoxComplete(false);
    setShowBox(false);
    setShowOverlay(false);
  };

  /**
   * Get the style for the modal
   * @returns 
   */
  const getModalStyle = (): React.CSSProperties => {
    const padding = 40; // 20px padding on top and bottom
    return {
      position: 'fixed',
      top: `${padding}px`,
      left: '50%',
      transform: 'translateX(-50%)', // Only transform X since we're using fixed top
      width: '500px',
      maxWidth: '500px',
      // height: `calc(100vh - ${padding * 2}px)`, // Full height minus padding
      backgroundColor: 'white',
      borderRadius: '8px',
      boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
      zIndex: 1000000,
      overflowY: 'auto',
      color: 'black',
    };
  };

  useEffect(() => {
    if (showOverlay) {
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [showOverlay]);

  return (
    <>
      {showOverlay && (
        <Box
          onClick={handleClick}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            background: 'rgba(0, 0, 0, 0.1)',
            zIndex: 999999,
            cursor: 'crosshair',
          }}
        />
      )}
      {showBox && boxTopLeft && boxBottomRight && (
        <Box
          style={{
            position: 'fixed',
            top: boxTopLeft.y,
            left: boxTopLeft.x,
            width: boxBottomRight.x - boxTopLeft.x,
            height: boxBottomRight.y - boxTopLeft.y,
            background: 'rgba(192, 90, 253, 0.5)',
            zIndex: 999999,
            cursor: 'crosshair',
          }}
        />
      )}
      {(coordinates || isBoxComplete) && screenshot && (
        <Modal 
          coordinates={coordinates}
          boxTopLeft={boxTopLeft}
          boxBottomRight={boxBottomRight}
          isBoxComplete={isBoxComplete}
          screenshot={screenshot}
          onClose={handleClose}
          style={getModalStyle()}
        />
      )}
    </>
  );
};

export default App;
