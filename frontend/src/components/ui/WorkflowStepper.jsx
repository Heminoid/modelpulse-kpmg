import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Database, Sliders, Activity, PlayCircle, FileText, Check } from 'lucide-react';
import './WorkflowStepper.css';

const STEPS = [
  { id: 'datasets', path: '/datasets', label: '1. Ingest Data', icon: Database },
  { id: 'monitors', path: '/monitors', label: '2. Configure Monitor', icon: Activity },
  { id: 'runs', path: '/runs', label: '3. Execute & Evaluate', icon: PlayCircle },
  { id: 'reports', path: '/reports', label: '4. Generate Reports', icon: FileText },
];

const WorkflowStepper = ({ currentStep }) => {
  const location = useLocation();
  const navigate = useNavigate();

  const getActiveIndex = () => {
    if (currentStep) {
      const idx = STEPS.findIndex(s => s.id === currentStep);
      if (idx !== -1) return idx;
    }
    const path = location.pathname;
    if (path.startsWith('/datasets')) return 0;
    if (path.startsWith('/monitors')) return 1;
    if (path.startsWith('/runs')) return 2;
    if (path.startsWith('/reports')) return 3;
    return -1;
  };

  const activeIdx = getActiveIndex();

  if (activeIdx === -1) return null;

  return (
    <div className="workflow-stepper-container">
      <div className="workflow-stepper">
        {STEPS.map((step, idx) => {
          const Icon = step.icon;
          const isCompleted = idx < activeIdx;
          const isActive = idx === activeIdx;

          return (
            <React.Fragment key={step.id}>
              <div 
                className={`stepper-step ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
                onClick={() => navigate(step.path)}
                title={`Go to ${step.label}`}
              >
                <div className="stepper-icon">
                  {isCompleted ? <Check size={14} /> : <Icon size={14} />}
                </div>
                <span className="stepper-label">{step.label}</span>
              </div>
              {idx < STEPS.length - 1 && (
                <div className={`stepper-line ${idx < activeIdx ? 'completed' : ''}`} />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

export default WorkflowStepper;
