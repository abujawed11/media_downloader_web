import { createBrowserRouter } from 'react-router-dom'
import App from '../App'
import Home from '../pages/Home'
import Downloads from '../pages/Downloads'
import Settings from '../pages/Settings'
import Library from '../pages/Library'
import Watch from '../pages/Watch'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Home /> },
      { path: 'downloads', element: <Downloads /> },
      { path: 'library', element: <Library /> },
      { path: 'watch/:id', element: <Watch /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
])
