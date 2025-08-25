import { createBrowserRouter } from 'react-router-dom'
import App from '../App'
import Home from '../pages/Home'
import Downloads from '../pages/Downloads'
import Settings from '../pages/Settings'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Home /> },
      { path: 'downloads', element: <Downloads /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
])
