import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Dialog,
  DialogTitle,
  DialogContent,
  Typography, 
  Box, 
  CircularProgress,
  Alert,
  IconButton,
  Divider,
  Grid,
  Card,
  CardContent
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';

// Helper function to format dates consistently
const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  try {
    const date = new Date(dateString);
    // Use a consistent date format
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    }).format(date);
  } catch (e) {
    console.error('Error formatting date:', e);
    return 'N/A';
  }
};

// Helper function to format chart dates (shorter format)
const formatChartDate = (dateString) => {
  if (!dateString) return '';
  try {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'numeric',
      day: 'numeric',
      year: '2-digit'
    }).format(date);
  } catch (e) {
    return '';
  }
};

function TitleAnalysis({ titleNumber, onClose }) {
  const { data: analysis, isLoading, error } = useQuery({
    queryKey: ['titleAnalysis', titleNumber],
    queryFn: async () => {
      const response = await fetch(`/api/titles/${titleNumber}/analysis`);
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    }
  });

  if (isLoading) return (
    <Dialog open fullWidth maxWidth="lg">
      <DialogContent>
        <Box display="flex" justifyContent="center" p={3}>
          <CircularProgress />
        </Box>
      </DialogContent>
    </Dialog>
  );

  if (error) return (
    <Dialog open fullWidth maxWidth="lg">
      <DialogContent>
        <Alert severity="error">Error loading analysis: {error.message}</Alert>
      </DialogContent>
    </Dialog>
  );

  // Prepare chart data with formatted dates
  const chartData = analysis.historical_data.dates.map((date, index) => ({
    date: formatChartDate(date),
    sections: analysis.historical_data.section_counts[index],
    parts: analysis.historical_data.part_counts[index]
  }));

  return (
    <Dialog open fullWidth maxWidth="lg">
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography variant="h6">
              Title {analysis.title_number}: {analysis.name}
            </Typography>
            <Typography variant="subtitle2" color="text.secondary">
              Last Updated: {formatDate(analysis.versions.latest_update)}
            </Typography>
          </Box>
          <IconButton onClick={onClose} edge="end">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={3}>
          {/* Overview Card */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Overview</Typography>
                <Divider sx={{ mb: 2 }} />
                <Box>
                  <Typography variant="body1" gutterBottom>
                    Total Parts: {analysis.structure.total_parts}
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    Total Sections: {analysis.structure.total_sections}
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    Total Versions: {analysis.versions.total_versions}
                  </Typography>
                  <Typography variant="body1">
                    Latest Update: {formatDate(analysis.versions.latest_update)}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Metrics Card */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Metrics</Typography>
                <Divider sx={{ mb: 2 }} />
                <Box>
                  <Typography variant="body1" gutterBottom>
                    Word Count: {analysis.metrics.word_count.toLocaleString()}
                  </Typography>
                  <Typography variant="body1">
                    Average Words per Section: {analysis.metrics.average_words_per_section.toLocaleString()}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Historical Changes Chart */}
          {chartData.length > 0 && (
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Historical Changes</Typography>
                  <Divider sx={{ mb: 2 }} />
                  <Box sx={{ height: 300 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={chartData}
                        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          dataKey="date"
                          angle={-45}
                          textAnchor="end"
                          height={60}
                        />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Line 
                          type="monotone" 
                          dataKey="sections" 
                          stroke="#8884d8" 
                          name="Sections"
                          dot={false}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="parts" 
                          stroke="#82ca9d" 
                          name="Parts"
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          )}

          {/* Corrections */}
          {analysis.corrections?.recent_corrections?.length > 0 && (
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Recent Corrections</Typography>
                  <Divider sx={{ mb: 2 }} />
                  {analysis.corrections.recent_corrections.map((correction, index) => (
                    <Box key={index} sx={{ mb: 2 }}>
                      <Typography variant="subtitle1">
                        {formatDate(correction.date)}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {correction.description}
                      </Typography>
                    </Box>
                  ))}
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      </DialogContent>
    </Dialog>
  );
}

export default TitleAnalysis;