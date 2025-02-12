import React, { useState } from 'react';
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
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  BarChart,
  Bar
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
  const [showAllAgencies, setShowAllAgencies] = useState(false);
  const [timeRange, setTimeRange] = useState('1y'); // Default to 1 year
  const TOP_AGENCIES_COUNT = 5; // Show top 5 agencies by default

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

  // Filter historical data based on time range
  const filterHistoricalData = (data) => {
    if (!data || !data.dates || data.dates.length === 0) return [];
    
    const now = new Date();
    const cutoffDate = new Date();
    
    switch (timeRange) {
      case '6m':
        cutoffDate.setMonth(now.getMonth() - 6);
        break;
      case '1y':
        cutoffDate.setFullYear(now.getFullYear() - 1);
        break;
      case '2y':
        cutoffDate.setFullYear(now.getFullYear() - 2);
        break;
      case '5y':
        cutoffDate.setFullYear(now.getFullYear() - 5);
        break;
      case 'all':
        return data.dates.map((date, index) => ({
          date: formatChartDate(date),
          sections: data.section_counts[index],
          parts: data.part_counts[index]
        }));
      default:
        cutoffDate.setFullYear(now.getFullYear() - 1);
    }

    const filteredData = data.dates
      .map((date, index) => ({
        date: new Date(date),
        formattedDate: formatChartDate(date),
        sections: data.section_counts[index],
        parts: data.part_counts[index]
      }))
      .filter(item => item.date >= cutoffDate)
      .map(item => ({
        date: item.formattedDate,
        sections: item.sections,
        parts: item.parts
      }));

    return filteredData;
  };

  // Prepare agency data for visualization
  const prepareAgencyData = (agencyWordCounts) => {
    if (!agencyWordCounts) return [];
    
    const sortedAgencies = Object.entries(agencyWordCounts)
      .sort(([, a], [, b]) => b - a)
      .map(([agency, count]) => ({
        agency,
        wordCount: count
      }));

    if (!showAllAgencies) {
      return sortedAgencies.slice(0, TOP_AGENCIES_COUNT);
    }
    return sortedAgencies;
  };

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

          {/* Agency Word Counts */}
          {analysis.metrics.agency_word_counts && 
           Object.keys(analysis.metrics.agency_word_counts).length > 0 && (
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6">
                      Word Count by Agency
                    </Typography>
                    <Button 
                      variant="outlined" 
                      size="small"
                      onClick={() => setShowAllAgencies(!showAllAgencies)}
                    >
                      {showAllAgencies ? 'Show Top 5' : 'Show All'}
                    </Button>
                  </Box>
                  <Divider sx={{ mb: 2 }} />
                  
                  {/* Table View */}
                  <TableContainer component={Paper} sx={{ mb: 3 }}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Agency</TableCell>
                          <TableCell align="right">Word Count</TableCell>
                          <TableCell align="right">Percentage</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {prepareAgencyData(analysis.metrics.agency_word_counts).map(({ agency, wordCount }) => {
                          const percentage = ((wordCount / analysis.metrics.word_count) * 100).toFixed(1);
                          return (
                            <TableRow key={agency}>
                              <TableCell component="th" scope="row">
                                <Tooltip title={agency}>
                                  <span>{agency.length > 40 ? `${agency.substring(0, 40)}...` : agency}</span>
                                </Tooltip>
                              </TableCell>
                              <TableCell align="right">
                                {wordCount.toLocaleString()}
                              </TableCell>
                              <TableCell align="right">
                                {percentage}%
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>

                  {/* Chart View */}
                  <Box sx={{ height: 300 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={prepareAgencyData(analysis.metrics.agency_word_counts)}
                        margin={{
                          top: 20,
                          right: 30,
                          left: 20,
                          bottom: 60
                        }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          dataKey="agency"
                          angle={-45}
                          textAnchor="end"
                          height={100}
                          interval={0}
                          tick={{ fontSize: 12 }}
                        />
                        <YAxis />
                        <RechartsTooltip 
                          formatter={(value) => [
                            `${value.toLocaleString()} words`,
                            'Word Count'
                          ]}
                        />
                        <Legend />
                        <Bar 
                          dataKey="wordCount" 
                          fill="#8884d8" 
                          name="Word Count"
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          )}

          {/* Historical Changes Chart */}
          {analysis.historical_data.dates.length > 0 && (
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6">
                      Historical Changes
                    </Typography>
                    <FormControl size="small" sx={{ minWidth: 120 }}>
                      <InputLabel>Time Range</InputLabel>
                      <Select
                        value={timeRange}
                        label="Time Range"
                        onChange={(e) => setTimeRange(e.target.value)}
                      >
                        <MenuItem value="6m">6 Months</MenuItem>
                        <MenuItem value="1y">1 Year</MenuItem>
                        <MenuItem value="2y">2 Years</MenuItem>
                        <MenuItem value="5y">5 Years</MenuItem>
                        <MenuItem value="all">All Time</MenuItem>
                      </Select>
                    </FormControl>
                  </Box>
                  <Divider sx={{ mb: 2 }} />
                  <Box sx={{ height: 300 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={filterHistoricalData(analysis.historical_data)}
                        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          dataKey="date"
                          angle={-45}
                          textAnchor="end"
                          height={60}
                          interval="preserveStartEnd"
                        />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Line 
                          type="monotone" 
                          dataKey="sections" 
                          stroke="#8884d8" 
                          name="Sections"
                          dot={true}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="parts" 
                          stroke="#82ca9d" 
                          name="Parts"
                          dot={true}
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