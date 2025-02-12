import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Card, 
  CardContent, 
  Grid, 
  Typography, 
  CircularProgress,
  Alert
} from '@mui/material';
import TitleAnalysis from './TitleAnalysis';

function TitlesOverview() {
  const [selectedTitle, setSelectedTitle] = useState(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['titles'],
    queryFn: async () => {
      try {
        const response = await fetch('/api/titles');
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }
        const data = await response.json();
        return data.titles; // Extract the titles array
      } catch (err) {
        console.error('Fetch error:', err);
        throw err;
      }
    }
  });

  if (isLoading) return <CircularProgress />;
  if (error) return <Alert severity="error">{error.message}</Alert>;
  if (!data) return <Alert severity="info">No titles found</Alert>;

  return (
    <div>
      <Typography variant="h4" gutterBottom>
        Federal Regulations Titles
      </Typography>
      <Grid container spacing={2}>
        {data.map((title) => (
          <Grid item xs={12} sm={6} md={4} key={title.number}>
            <Card 
              sx={{ 
                cursor: 'pointer',
                '&:hover': { backgroundColor: '#f5f5f5' }
              }}
              onClick={() => setSelectedTitle(title.number)}
            >
              <CardContent>
                <Typography variant="h6">
                  Title {title.number}
                </Typography>
                <Typography color="textSecondary">
                  {title.name}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Last Updated: {new Date(title.latest_issue_date).toLocaleDateString()}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {selectedTitle && (
        <TitleAnalysis 
          titleNumber={selectedTitle} 
          onClose={() => setSelectedTitle(null)}
        />
      )}
    </div>
  );
}

export default TitlesOverview; 