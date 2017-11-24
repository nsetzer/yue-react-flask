import * as React from 'react';
import { Link } from 'react-router-dom'


const logo = require('../svg/logo.svg');
import './App.css';

import RandomInt from './RandomInt'
import TestMessage from './TestMessage'

export interface TestViewProps {}

export interface TestViewState {}

class TestView extends React.Component<TestViewProps,TestViewState> {

  constructor(props : any) {
    super(props);
  }

  render() {
    return (
      <div>
        <div className="App">
          <header className="App-header">
            <img src={logo} className="App-logo" alt="logo" />
            <h1 className="App-title">Welcome to React</h1>
          </header>

          <br/>
          <p>
          <Link to="/">&nbsp;Home&nbsp;</Link>
          <Link to="/login">&nbsp;Login&nbsp;</Link>
          <Link to="/register">&nbsp;Register&nbsp;</Link>
          <Link to="/about/React">&nbsp;About&nbsp;</Link>
          </p>

        </div>

        <div className="container-fluid content-body">
          <RandomInt/>
          <TestMessage/>
        </div>

      </div>

    );
  }
}

export default TestView;
