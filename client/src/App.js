import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Container, CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import TitlesOverview from './components/TitlesOverview';

const queryClient = new QueryClient();
const theme = createTheme({
  palette: {
    mode: 'light',
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Container maxWidth="lg">
          <h1>eCFR Analysis Dashboard</h1>
          <TitlesOverview />
        </Container>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;