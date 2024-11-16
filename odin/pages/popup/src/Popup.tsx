import '@src/Popup.css';
import React, { useState, useEffect } from 'react';
import { type ClickWithItems } from '@extension/shared/lib/hooks/types';
import { fetchRecentClicks, fetchClickItems } from '@extension/shared/lib/hooks/api';
import { useStorage, withErrorBoundary, withSuspense } from '@extension/shared';
import CircularProgress from '@mui/material/CircularProgress';
import { profileStorage } from '@extension/storage';
import { Box, Button, Typography } from '@mui/material';
import { v4 as uuid } from 'uuid';


const notificationOptions = {
  type: 'basic',
  iconUrl: chrome.runtime.getURL('icon-34.png'),
  title: 'Injecting content script error',
  message: 'You cannot inject script here!',
} as const;

const Popup = () => {
  const profile = useStorage(profileStorage);
  const [recentClicks, setRecentClicks] = useState<ClickWithItems[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    setIsLoading(true);
    (async () => {
      try {
        const id = profile.id ?? uuid();
        if (!id) {
          profileStorage.setId(id);
        }
        const clicks = await fetchRecentClicks(id, 5);
        const clicksWithItems = await Promise.all(clicks.map(async (click) => {
          const items = await fetchClickItems(click.click_id, 4);
          return { ...click, items: items || [] };
        }));
        setRecentClicks(clicksWithItems.filter(c => c.items.length > 0));
      } catch (err) {
        console.error('Failed to load previous searches', err);
      } finally {
        setIsLoading(false);
      }
    })()
  }, [profile.id]);

  const injectClickScript = async () => {
    const [tab] = await chrome.tabs.query({ currentWindow: true, active: true });
    if (!tab.id || !tab.url) return;

    if (tab.url.startsWith('about:') || tab.url.startsWith('chrome:')) {
      chrome.notifications.create('inject-error', notificationOptions);
    }
    const imageUri = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png' });
    await chrome.scripting
      .executeScript({
        target: { tabId: tab.id },
        files: ['/content-runtime/index.iife.js'],
      })
      .catch(err => {
        // Handling errors related to other paths
        if (err.message.includes('Cannot access a chrome:// URL')) {
          chrome.notifications.create('inject-error', notificationOptions);
        }
      });
    
    await chrome.tabs.sendMessage(tab.id, {
      type: 'SET_SCREENSHOT',
      payload: imageUri
    });

    window.close();
  };

  return (
    <Box>
      <Box 
        sx={{ 
          display: "flex", 
          flexDirection: "row", 
          justifyContent: "space-between", 
          alignItems: "center", 
          gap: 2, 
          position: 'sticky',
          top: 0,
          backgroundColor: 'white',
          zIndex: 1000,
          padding: '16px',
          borderBottom: '1px solid rgba(0, 0, 0, 0.12)'  // Optional: add border
        }}
      >
        <Button 
          sx={{ 
            backgroundColor: "#C05AFD", 
            color: "white", 
            fontWeight: "bold", 
            borderRadius: 10, 
            px: 1,
          }} 
          onClick={injectClickScript}
          fullWidth
        >
          <img src={chrome.runtime.getURL('popup/logo.svg')} alt="logo" style={{ width: '30px', height: '30px' }} />
          <Typography sx={{ fontFamily: "Lexend", fontWeight: "bold" }}>
            Activate
          </Typography>
        </Button>
      </Box>
      {isLoading && (
        <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", my: 4 }}>
          <CircularProgress sx={{ color: "#C05AFD" }} />
        </Box>
      )}
      {recentClicks.length > 0 && (
        
        <Box 
          sx={{ 
            mx: 4, 
            my: 2, 
            // overflowY: "scroll" 
          }}
        >
          <Typography 
            sx={{ 
              fontFamily: "Lexend", 
              fontWeight: "bold", 
              fontSize: 20,
            }}
          >
            Past Searches ({recentClicks.length})
          </Typography>
          <div className="my-3" />
          <Box 
            sx={{ 
              display: "flex", 
              flexDirection: "column",
              gap: 2, 
            }}
          >
            {recentClicks.map((click, index) => (
              <React.Fragment key={click.click_id}>
                <SearchResult click={click} />
                {index < recentClicks.length - 1 && (
                  <div style={{ 
                    height: '1px',
                    backgroundColor: 'rgba(0, 0, 0, 0.12)',
                  }} />
                )}
              </React.Fragment>
            ))}
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default withErrorBoundary(withSuspense(Popup, <div> Loading ... </div>), <div> Error Occurred</div>);

const SearchResult = ({ click }: { click: ClickWithItems }) => {
  const minPrice = click.items
    .reduce((min, item) => Math.min(min, item.price_value), Infinity);
  
  return (
    <Box sx={{ my: 1 }}>
      <Box 
        sx={{ 
          display: "flex", 
          flexDirection: "row", 
          justifyContent: "space-between", 
          gap: 2,
          mb: 2,
        }}
      >
        <Typography 
          sx={{ 
            fontFamily: "Lexend", 
            fontWeight: "semibold"
          }}
          style={{
            display: '-webkit-box',       // Ensures the element behaves like a block with constrained lines
            WebkitLineClamp: 2,           // Limits the text to 2 lines
            WebkitBoxOrient: 'vertical',  // Sets the box’s orientation to vertical
            overflow: 'hidden',           // Hides overflowing text
            textOverflow: 'ellipsis',     // Displays "..." for overflowing text
          }}
        >
          {click.description}
        </Typography>
        <Typography 
          sx={{ 
            fontFamily: "Lexend", 
            fontWeight: "semibold", 
            color: "#958B8B"
          }}
        >
          {`$${minPrice.toFixed(2)}+`}
        </Typography>
      </Box>
      <Box 
        sx={{ 
          display: "flex", 
          flexDirection: "row", 
          alignItems: "center",
          gap: 2, 
          mb: 1, 
          // overflowX: "auto",
        }}>
        {click.items.map((item) => (
          <img 
            key={item.item_id}
            src={item.thumbnail!} 
            alt={item.title}
            style={{ 
              width: '60px', 
              height: '60px',
              objectFit: 'cover',
              borderRadius: '4px'
            }}
          />
        ))}
        <div className="flex-1" />
        <img 
          src={chrome.runtime.getURL('popup/arrow-right.svg')} 
          alt="arrow right" 
          style={{ width: '30px', height: '30px' }} 
        />
      </Box>
      {click.channel && 
        <Typography 
          sx={{ 
            fontFamily: "Lexend", 
            color: "#BEBEBE",
            mt: 1,
            fontSize: 14,
          }}
          gutterBottom
        >
          searched from {click.channel.replace("www.", "")}
        </Typography>}
    </Box>
  )
}