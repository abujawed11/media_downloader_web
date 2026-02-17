import { createBrowserRouter, Navigate } from 'react-router-dom'
import App from '../App'
import Home from '../pages/Home'
import Uploads from '../pages/Uploads'
import Settings from '../pages/Settings'
import Library from '../pages/Library'
import Watch from '../pages/Watch'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Home /> },
      { path: 'uploads', element: <Uploads /> },
      { path: 'downloads', element: <Navigate to="/uploads" replace /> }, // old URL redirect
      { path: 'library', element: <Library /> },
      { path: 'watch/:id', element: <Watch /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
])
